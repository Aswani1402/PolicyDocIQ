import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import EMBEDDING_DEVICE, EMBEDDING_MODEL_NAME, QDRANT_COLLECTION_NAME, QDRANT_PATH
from src.retriever import QdrantRAGRetriever


TEST_QUESTIONS = [
    "What is Qatar's projected GDP growth for 2024 and 2025?",
    "What are the main risks to Qatar's economic outlook?",
    "What does the report say about VAT?",
    "Summarize Qatar's banking sector condition.",
]


def main() -> None:
    print("PolicyDocIQ Step 4: test retrieval against existing Qdrant collection")
    print(f"Qdrant path: {QDRANT_PATH}")
    print(f"Collection: {QDRANT_COLLECTION_NAME}")
    print("This script does not extract, chunk, or re-index.")

    retriever = QdrantRAGRetriever(
        collection_name=QDRANT_COLLECTION_NAME,
        qdrant_path=str(QDRANT_PATH),
        embedding_model_name=EMBEDDING_MODEL_NAME,
        device=EMBEDDING_DEVICE
    )

    if not retriever.collection_exists():
        raise ValueError(
            f"Collection not found: {QDRANT_COLLECTION_NAME}. "
            "Run `python scripts/02_index_qdrant.py` first."
        )

    print("Existing point count:", retriever.point_count())
    print("\nLoading BGE-M3 for query embeddings...")

    print("\nRetrieval test")
    print("--------------")

    for question in TEST_QUESTIONS:
        print("\nQuestion:", question)

        results = retriever.search(
            query=question,
            top_k=3
        )

        for rank, result in enumerate(results, start=1):
            print(f"\nRank {rank}")
            print("Score:", round(result["score"], 4))
            print("Page:", result["page_number"])
            print("Section:", result["section_title"])
            print("Snippet:", result["text"][:600])


if __name__ == "__main__":
    main()
