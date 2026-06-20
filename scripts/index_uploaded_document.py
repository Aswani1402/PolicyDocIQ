from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.pdf_loader import extract_pages_with_pymupdf, save_dataframe
from src.chunker import build_chunks_from_pages, save_chunks
from src.retriever import QdrantRAGRetriever
from src.table_extractor import extract_tables_from_pdf
from src.document_manager import (
    collection_name_from_document_id,
    add_document_record,
    OUTPUTS_DIR
)


def index_document(
    pdf_path: str,
    document_id: str,
    recreate_collection: bool = True,
    qdrant_client=None,
    original_filename: str = None,
    embedder=None,
):
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    collection_name = collection_name_from_document_id(document_id)

    document_output_dir = OUTPUTS_DIR / document_id
    document_output_dir.mkdir(parents=True, exist_ok=True)

    pages_csv_path = document_output_dir / "extracted_pages.csv"
    chunks_csv_path = document_output_dir / "extracted_chunks.csv"
    tables_output_dir = PROJECT_ROOT / "outputs" / "tables" / document_id
    tables_json_path = tables_output_dir / "tables.json"
    tables_csv_path = tables_output_dir / "tables.csv"

    print(f"Indexing document: {pdf_path.name}")
    print(f"Document ID: {document_id}")
    print(f"Collection: {collection_name}")

    print("Extracting pages...")
    pages_df = extract_pages_with_pymupdf(str(pdf_path))
    if original_filename:
        pages_df["document_name"] = original_filename
    save_dataframe(pages_df, str(pages_csv_path))

    print("Creating chunks...")
    chunks_df = build_chunks_from_pages(
        pages_df=pages_df,
        chunk_size=350,
        overlap=60
    )
    save_chunks(chunks_df, str(chunks_csv_path))

    table_count = 0
    table_error = None

    try:
        print("Extracting tables...")
        tables = extract_tables_from_pdf(
            pdf_path=str(pdf_path),
            document_id=document_id,
            output_dir=str(tables_output_dir),
        )
        table_count = len(tables)
        print(f"Extracted tables: {table_count}")
    except Exception as error:
        table_error = str(error)
        print(f"Table extraction failed; continuing document indexing: {table_error}")

    print("Indexing chunks into Qdrant...")
    retriever = QdrantRAGRetriever(
        collection_name=collection_name,
        qdrant_path=str(PROJECT_ROOT / "outputs" / "qdrant_db"),
        embedding_model_name="BAAI/bge-m3",
        device="cpu",
        client=qdrant_client,
        embedder=embedder,
    )

    retriever.create_collection(recreate=recreate_collection)
    retriever.index_chunks(
        chunks_csv_path=str(chunks_csv_path),
        batch_size=4
    )

    count_result = retriever.client.count(
        collection_name=collection_name,
        exact=True
    )

    record = {
        "document_id": document_id,
        "filename": original_filename or pdf_path.name,
        "pdf_path": str(pdf_path),
        "pages_csv_path": str(pages_csv_path),
        "chunks_csv_path": str(chunks_csv_path),
        "tables_json_path": str(tables_json_path),
        "tables_csv_path": str(tables_csv_path),
        "table_count": table_count,
        "collection_name": collection_name,
        "pages": int(len(pages_df)),
        "chunks": int(len(chunks_df)),
        "qdrant_points": int(count_result.count),
        "uploaded_at": __import__("datetime").datetime.now().isoformat()
    }

    if table_error:
        record["table_error"] = table_error

    add_document_record(record)

    print("Indexing complete.")
    print(record)

    return record
