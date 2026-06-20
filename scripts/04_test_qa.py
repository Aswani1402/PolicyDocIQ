from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.retriever import QdrantRAGRetriever
from src.qa_engine import EvidenceBasedQAEngine


def main():
    print("PolicyDocIQ Step 4: QA test with citation-backed evidence")

    retriever = QdrantRAGRetriever(
        collection_name="policydociq_qatar",
        qdrant_path=str(PROJECT_ROOT / "outputs" / "qdrant_db"),
        embedding_model_name="BAAI/bge-m3",
        device="cpu"
    )

    qa_engine = EvidenceBasedQAEngine(min_score=0.45)

    questions = [
        "What is Qatar's projected GDP growth for 2024 and 2025?",
        "What are the main risks to Qatar's economic outlook?",
        "What does the report say about VAT?",
        "Summarize Qatar's banking sector condition."
    ]

    for question in questions:
        print("\n" + "=" * 80)
        print("Question:", question)

        retrieved_chunks = retriever.search(
            query=question,
            top_k=5
        )

        result = qa_engine.generate_answer(
            question=question,
            retrieved_chunks=retrieved_chunks
        )

        print("\nAnswer")
        print("------")
        print(result["answer"])

        print("\nCitations")
        print("---------")
        print(result["citations"])

        print("\nTop evidence pages")
        print("------------------")
        for chunk in retrieved_chunks[:3]:
            print(
                f"Page {chunk['page_number']} | "
                f"Score {round(chunk['score'], 4)} | "
                f"Section: {chunk['section_title']}"
            )


if __name__ == "__main__":
    main()