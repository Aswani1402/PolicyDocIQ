import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    EMBEDDING_DEVICE,
    EMBEDDING_MODEL_NAME,
    EXTRACTED_CHUNKS_PATH,
    QDRANT_COLLECTION_NAME,
    QDRANT_PATH,
)
from src.retriever import QdrantRAGRetriever


# Set this to True when you intentionally want to delete and rebuild the
# existing collection. Keep False to preserve it and upsert current chunk IDs.
RECREATE_COLLECTION = False

# Qdrant local mode is single-process. On Windows, only one Python process
# should access outputs/qdrant_db at a time. If locked, close the other terminal
# or kill the stale python.exe process before rerunning this script.


def main() -> None:
    print("PolicyDocIQ Step 2: index chunks into local Qdrant")
    print(f"Chunks CSV: {EXTRACTED_CHUNKS_PATH}")
    print(f"Qdrant path: {QDRANT_PATH}")
    print(f"Collection: {QDRANT_COLLECTION_NAME}")
    print(f"Recreate collection: {RECREATE_COLLECTION}")

    if not EXTRACTED_CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"Missing chunks file: {EXTRACTED_CHUNKS_PATH}\n"
            "Run `python scripts/01_extract_and_chunk.py` first."
        )

    retriever = QdrantRAGRetriever(
        collection_name=QDRANT_COLLECTION_NAME,
        qdrant_path=str(QDRANT_PATH),
        embedding_model_name=EMBEDDING_MODEL_NAME,
        device=EMBEDDING_DEVICE
    )

    if retriever.collection_exists():
        print(f"Collection already exists: {QDRANT_COLLECTION_NAME}")
        print("Change RECREATE_COLLECTION to True in this script to rebuild from scratch.")

    retriever.create_collection(recreate=RECREATE_COLLECTION)
    retriever.index_chunks(
        chunks_csv_path=str(EXTRACTED_CHUNKS_PATH),
        batch_size=4
    )

    print("\nIndexing complete")
    print("-----------------")
    print("Point count:", retriever.point_count())


if __name__ == "__main__":
    main()
