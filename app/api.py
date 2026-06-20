import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.retriever import QdrantRAGRetriever
from src.qa_engine import EvidenceBasedQAEngine
from src.reranker import CrossEncoderReranker

from src.document_manager import (
    DOCUMENTS_DIR,
    OUTPUTS_DIR as DOCUMENT_OUTPUTS_DIR,
    ensure_document_dirs,
    slugify_filename,
    list_documents,
    get_document,
    collection_name_from_document_id,
)

from scripts.index_uploaded_document import index_document


PROJECT_ROOT = Path(__file__).resolve().parents[1]

QDRANT_PATH = PROJECT_ROOT / "outputs" / "qdrant_db"
TABLES_PATH = PROJECT_ROOT / "outputs" / "tables"
COLLECTION_NAME = "policydociq_qatar"

retriever: Optional[QdrantRAGRetriever] = None
qa_engine: Optional[EvidenceBasedQAEngine] = None
reranker: Optional[CrossEncoderReranker] = None
document_retrievers: Dict[str, QdrantRAGRetriever] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield

    if retriever is not None:
        retriever.client.close()


app = FastAPI(
    title="PolicyDocIQ API",
    description="Citation-backed RAG API for IMF economic reports.",
    version="0.2.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int = Field(default=5, ge=1, le=10)
    use_reranker: bool = True
    rerank_pool: int = Field(default=20, ge=5, le=50)

class DocumentQueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int = Field(default=5, ge=1, le=10)
    use_reranker: bool = True
    rerank_pool: int = Field(default=20, ge=5, le=50)

class EvidenceItem(BaseModel):
    score: float
    retrieval_score: Optional[float] = None
    rerank_score: Optional[float] = None
    chunk_id: Optional[str]
    page_number: Optional[int]
    section_title: Optional[str]
    document_name: Optional[str]
    text: Optional[str]


class QueryResponse(BaseModel):
    question: str
    answer: str
    citations: List[int]
    evidence: List[EvidenceItem]


class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    collection_name: str
    pages: int
    chunks: int
    qdrant_points: int
    table_count: int = 0
    uploaded_at: str


def format_evidence_items(qa_result: Dict[str, Any]) -> List[EvidenceItem]:
    evidence_items = []

    for item in qa_result["evidence"]:
        evidence_items.append(
            EvidenceItem(
                score=item.get("score"),
                retrieval_score=item.get("retrieval_score"),
                rerank_score=item.get("rerank_score"),
                chunk_id=item.get("chunk_id"),
                page_number=item.get("page_number"),
                section_title=item.get("section_title"),
                document_name=item.get("document_name"),
                text=item.get("text"),
            )
        )

    return evidence_items


def load_document_tables(document: Dict[str, Any]) -> List[Dict[str, Any]]:
    document_id = document["document_id"]
    configured_path = document.get("tables_json_path")
    tables_path = (
        Path(configured_path)
        if configured_path
        else PROJECT_ROOT / "outputs" / "tables" / document_id / "tables.json"
    )

    if not tables_path.exists():
        return []

    try:
        with tables_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read extracted tables for {document_id}: {error}",
        ) from error

    return data if isinstance(data, list) else []


def table_matches_query(table: Dict[str, Any], query: str) -> bool:
    return query.casefold() in str(table.get("table_text") or "").casefold()


def get_rag_components():
    """
    Load default Qatar retriever and QA engine once.

    Important for Windows/Qdrant local mode:
    - Do not run multiple API/server processes using the same outputs/qdrant_db folder.
    - Do not use uvicorn --reload for now.
    """

    global retriever, qa_engine

    if retriever is None:
        if not QDRANT_PATH.exists():
            raise RuntimeError(
                f"Qdrant DB not found at {QDRANT_PATH}. "
                "Run scripts/02_index_qdrant.py first."
            )

        retriever = QdrantRAGRetriever(
            collection_name=COLLECTION_NAME,
            qdrant_path=str(QDRANT_PATH),
            embedding_model_name="BAAI/bge-m3",
            device="cpu",
        )

    if qa_engine is None:
        qa_engine = EvidenceBasedQAEngine(min_score=0.45)

    return retriever, qa_engine

def get_reranker() -> CrossEncoderReranker:
    """
    Load reranker once.

    First load can take time because the model downloads locally.
    """

    global reranker

    if reranker is None:
        reranker = CrossEncoderReranker(
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
            device="cpu",
        )

    return reranker


def get_document_retriever(document_id: str) -> QdrantRAGRetriever:
    if document_id not in document_retrievers:
        default_retriever, _ = get_rag_components()
        document_retrievers[document_id] = QdrantRAGRetriever(
            collection_name=collection_name_from_document_id(document_id),
            qdrant_path=str(QDRANT_PATH),
            embedding_model_name="BAAI/bge-m3",
            device="cpu",
            client=default_retriever.client,
            embedder=default_retriever._ensure_embedder(),
        )

    return document_retrievers[document_id]


@app.get("/")
def home() -> Dict[str, Any]:
    return {
        "message": "Welcome to PolicyDocIQ API",
        "docs": "http://127.0.0.1:8000/docs",
        "health": "http://127.0.0.1:8000/health",
    }


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "project": "PolicyDocIQ",
        "message": "API is running",
    }


@app.get("/collection")
def collection_info() -> Dict[str, Any]:
    """
    Show default Qatar collection information.
    """

    try:
        rag_retriever, _ = get_rag_components()

        count_result = rag_retriever.client.count(
            collection_name=COLLECTION_NAME,
            exact=True,
        )

        return {
            "collection_name": COLLECTION_NAME,
            "qdrant_path": str(QDRANT_PATH),
            "points": count_result.count,
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/query", response_model=QueryResponse)
def query_document(request: QueryRequest) -> QueryResponse:
    """
    Query the default Qatar IMF report collection.
    """

    try:
        rag_retriever, rag_qa_engine = get_rag_components()

        initial_top_k = request.rerank_pool if request.use_reranker else request.top_k

        retrieved_chunks = rag_retriever.search(
            query=request.question,
            top_k=initial_top_k,
        )

        if request.use_reranker:
            active_reranker = get_reranker()
            retrieved_chunks = active_reranker.rerank(
                query=request.question,
                retrieved_chunks=retrieved_chunks,
                top_k=request.top_k,
            )

        qa_result = rag_qa_engine.generate_answer(
            question=request.question,
            retrieved_chunks=retrieved_chunks,
        )

        return QueryResponse(
            question=request.question,
            answer=qa_result["answer"],
            citations=qa_result["citations"],
            evidence=format_evidence_items(qa_result),
        )

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/documents")
def get_documents() -> Dict[str, Any]:
    """
    List all uploaded/indexed documents.
    """

    documents = []

    for document in list_documents():
        enriched_document = dict(document)
        if "table_count" not in enriched_document:
            enriched_document["table_count"] = len(load_document_tables(document))
        documents.append(enriched_document)

    return {"documents": documents}


@app.get("/documents/{document_id}/tables")
def get_document_tables(document_id: str) -> Dict[str, Any]:
    document = get_document(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    return {"tables": load_document_tables(document)}


@app.get("/documents/{document_id}/tables/search")
def search_document_tables(
    document_id: str,
    query: str = Query(..., min_length=1),
) -> Dict[str, Any]:
    document = get_document(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    tables = [
        table
        for table in load_document_tables(document)
        if table_matches_query(table, query)
    ]
    return {"query": query, "tables": tables}


@app.get("/tables/search")
def search_all_tables(query: str = Query(..., min_length=1)) -> Dict[str, Any]:
    matches = []

    for document in list_documents():
        for table in load_document_tables(document):
            if not table_matches_query(table, query):
                continue

            table_text = str(table.get("table_text") or "")
            matches.append(
                {
                    "document_id": document["document_id"],
                    "filename": document.get("filename"),
                    "page_number": table.get("page_number"),
                    "table_id": table.get("table_id"),
                    "rows": table.get("rows"),
                    "columns": table.get("columns"),
                    "table_text": table_text,
                    "table_text_preview": table_text[:500],
                }
            )

    return {"query": query, "tables": matches}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a PDF, extract pages, chunk text, embed chunks, and index into Qdrant.

    Warning:
    This can take time because BGE-M3 runs locally on CPU.
    """

    ensure_document_dirs()

    if file.filename is None:
        raise HTTPException(status_code=400, detail="Uploaded file has no filename.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    document_id = slugify_filename(file.filename)
    save_path = DOCUMENTS_DIR / f"{document_id}.pdf"

    try:
        default_retriever, _ = get_rag_components()

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        record = index_document(
            pdf_path=str(save_path),
            document_id=document_id,
            recreate_collection=True,
            qdrant_client=default_retriever.client,
            original_filename=file.filename,
            embedder=default_retriever._ensure_embedder(),
        )
        document_retrievers.pop(document_id, None)

        return {
            "message": "Document uploaded and indexed successfully.",
            "document": record,
        }

    except Exception as error:
        save_path.unlink(missing_ok=True)
        shutil.rmtree(DOCUMENT_OUTPUTS_DIR / document_id, ignore_errors=True)
        shutil.rmtree(TABLES_PATH / document_id, ignore_errors=True)

        if retriever is not None:
            upload_collection = collection_name_from_document_id(document_id)
            if upload_collection in retriever.list_collections():
                retriever.client.delete_collection(collection_name=upload_collection)

        raise HTTPException(status_code=500, detail=str(error))
    finally:
        await file.close()


@app.post("/documents/{document_id}/query", response_model=QueryResponse)
def query_uploaded_document(
    document_id: str,
    request: DocumentQueryRequest,
) -> QueryResponse:
    """
    Query a selected uploaded document by document_id.
    """

    document = get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_id}",
        )

    collection_name = document["collection_name"]

    try:
        document_retriever = get_document_retriever(document_id)
        _, document_qa_engine = get_rag_components()

        if document_retriever.collection_name != collection_name:
            document_retrievers.pop(document_id, None)
            document_retriever = get_document_retriever(document_id)

        initial_top_k = request.rerank_pool if request.use_reranker else request.top_k

        retrieved_chunks = document_retriever.search(
            query=request.question,
            top_k=initial_top_k,
        )

        if request.use_reranker:
            active_reranker = get_reranker()
            retrieved_chunks = active_reranker.rerank(
                query=request.question,
                retrieved_chunks=retrieved_chunks,
                top_k=request.top_k,
            )

        qa_result = document_qa_engine.generate_answer(
            question=request.question,
            retrieved_chunks=retrieved_chunks,
        )

        return QueryResponse(
            question=request.question,
            answer=qa_result["answer"],
            citations=qa_result["citations"],
            evidence=format_evidence_items(qa_result),
        )

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
