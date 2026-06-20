from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from src.embedder import BGEM3Embedder


class QdrantRAGRetriever:
    """
    Qdrant-based dense retriever for PolicyDocIQ.

    Stores:
    - chunk text
    - page number
    - section title
    - document name
    """

    def __init__(
        self,
        collection_name: str = "policydociq_qatar",
        qdrant_path: str = "outputs/qdrant_db",
        embedding_model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        load_embedder: bool = False,
        client: Optional[QdrantClient] = None,
        embedder: Optional[BGEM3Embedder] = None
    ):
        self.collection_name = collection_name
        self.qdrant_path = str(qdrant_path)
        self.embedding_model_name = embedding_model_name
        self.device = device
        self.embedder: Optional[BGEM3Embedder] = embedder

        Path(qdrant_path).mkdir(parents=True, exist_ok=True)

        if client is not None:
            self.client = client
        else:
            try:
                self.client = QdrantClient(path=str(qdrant_path))
            except RuntimeError as error:
                raise RuntimeError(
                    "Could not open local Qdrant storage. Qdrant local mode allows "
                    "only one Python process to access the storage folder at a time. "
                    "Close other PolicyDocIQ terminals or kill stale python.exe "
                    f"processes, then retry. Storage path: {qdrant_path}"
                ) from error

        if load_embedder:
            self._ensure_embedder()

    def _ensure_embedder(self) -> BGEM3Embedder:
        """
        Load the local embedding model only when a workflow needs embeddings.
        """

        if self.embedder is None:
            self.embedder = BGEM3Embedder(
                model_name=self.embedding_model_name,
                device=self.device
            )

        return self.embedder

    def list_collections(self) -> List[str]:
        """
        Return collection names in the local Qdrant store.
        """

        return [
            collection.name
            for collection in self.client.get_collections().collections
        ]

    def collection_exists(self) -> bool:
        """
        Check whether the configured collection exists.
        """

        return self.collection_name in self.list_collections()

    def point_count(self) -> int:
        """
        Return the number of points in the configured collection.
        """

        if not self.collection_exists():
            return 0

        return self.client.count(
            collection_name=self.collection_name,
            exact=True
        ).count

    def create_collection(self, recreate: bool = True) -> None:
        """
        Create or recreate Qdrant collection.
        """

        existing_collections = self.list_collections()

        if self.collection_name in existing_collections and recreate:
            print(f"Deleting existing collection: {self.collection_name}")
            self.client.delete_collection(collection_name=self.collection_name)
        elif self.collection_name in existing_collections:
            print(f"Using existing collection without deleting it: {self.collection_name}")
            return

        if not self.collection_exists():
            print(f"Creating collection: {self.collection_name}")
            embedder = self._ensure_embedder()

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=embedder.embedding_dim,
                    distance=Distance.COSINE
                )
            )

    def index_chunks(
        self,
        chunks_csv_path: str = "outputs/extracted_chunks.csv",
        batch_size: int = 4
    ) -> None:
        """
        Read chunks CSV, embed chunk texts, and store them in Qdrant.
        """

        chunks_path = Path(chunks_csv_path)

        if not chunks_path.exists():
            raise FileNotFoundError(
                f"Chunks file not found: {chunks_path}. "
                "Run `python scripts/01_extract_and_chunk.py` first."
            )

        print(f"Loading chunks from: {chunks_path}")
        chunks_df = pd.read_csv(chunks_path)

        if len(chunks_df) == 0:
            raise ValueError("Chunks CSV is empty.")

        required_columns = {
            "chunk_id",
            "document_name",
            "page_number",
            "section_title",
            "chunk_type",
            "text",
            "word_count",
            "char_count"
        }

        missing_columns = required_columns - set(chunks_df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        print(f"Loaded chunks: {len(chunks_df)}")
        print("Generating embeddings...")

        texts = chunks_df["text"].fillna("").tolist()
        embedder = self._ensure_embedder()

        embeddings = embedder.encode_texts(
            texts=texts,
            batch_size=batch_size,
            normalize_embeddings=True
        )

        print("Uploading embeddings to Qdrant...")

        points = []

        for idx, row in chunks_df.iterrows():
            payload = {
                "chunk_id": str(row["chunk_id"]),
                "document_name": str(row["document_name"]),
                "page_number": int(row["page_number"]),
                "section_title": "" if pd.isna(row["section_title"]) else str(row["section_title"]),
                "chunk_type": str(row["chunk_type"]),
                "text": str(row["text"]),
                "word_count": int(row["word_count"]),
                "char_count": int(row["char_count"])
            }

            points.append(
                PointStruct(
                    id=idx + 1,
                    vector=embeddings[idx].tolist(),
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(f"Indexed {len(points)} chunks into Qdrant collection: {self.collection_name}")

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search Qdrant for top-k relevant chunks.
        Compatible with newer qdrant-client versions using query_points().
        """

        if not self.collection_exists():
            raise ValueError(
                f"Qdrant collection does not exist: {self.collection_name}. "
                "Run `python scripts/02_index_qdrant.py` first."
            )

        embedder = self._ensure_embedder()
        query_vector = embedder.encode_query(query).tolist()

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )

        results = response.points

        formatted_results = []

        for result in results:
            payload = result.payload or {}

            formatted_results.append(
                {
                    "score": float(result.score),
                    "chunk_id": payload.get("chunk_id"),
                    "page_number": payload.get("page_number"),
                    "section_title": payload.get("section_title"),
                    "text": payload.get("text"),
                    "document_name": payload.get("document_name")
                }
            )

        return formatted_results
