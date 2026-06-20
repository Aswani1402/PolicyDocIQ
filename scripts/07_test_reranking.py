from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.retriever import QdrantRAGRetriever
from src.reranker import CrossEncoderReranker
from src.qa_engine import EvidenceBasedQAEngine


def main():
    print("PolicyDocIQ Step 9: Test reranking")
    print("----------------------------------")

    retriever = QdrantRAGRetriever(
        collection_name="policydociq_qatar",
        qdrant_path=str(PROJECT_ROOT / "outputs" / "qdrant_db"),
        embedding_model_name="BAAI/bge-m3",
        device="cpu"
    )

    reranker = CrossEncoderReranker(
        model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        device="cpu",
    )

    qa_engine = EvidenceBasedQAEngine(min_score=0.45)

    questions = [
        "What is Qatar's projected GDP growth for 2024 and 2025?",
        "What are the main risks to Qatar's economic outlook?",
        "What does the report say about VAT?",
        "Summarize Qatar's banking sector condition.",
        "What does the report say about LNG expansion?"
    ]

    for question in questions:
        print("\n" + "=" * 90)
        print("Question:", question)

        print("\nRetrieving top 20 chunks from Qdrant...")
        retrieved_chunks = retriever.search(
            query=question,
            top_k=20
        )

        print("\nTop 5 before reranking")
        print("----------------------")
        for rank, chunk in enumerate(retrieved_chunks[:5], start=1):
            print(
                f"Rank {rank} | "
                f"Page {chunk['page_number']} | "
                f"Retrieval score {round(chunk['score'], 4)}"
            )
        before_pages = [chunk.get("page_number") for chunk in retrieved_chunks[:5]]

        print("\nReranking top 20 chunks...")
        reranked_chunks = reranker.rerank(
            query=question,
            retrieved_chunks=retrieved_chunks,
            top_k=5
        )

        print("\nTop 5 after reranking")
        print("---------------------")
        for rank, chunk in enumerate(reranked_chunks, start=1):
            print(
                f"Rank {rank} | "
                f"Page {chunk['page_number']} | "
                f"Rerank score {round(chunk['rerank_score'], 4)} | "
                f"Original retrieval score {round(chunk['retrieval_score'], 4)}"
            )
            print("Snippet:", chunk["text"][:300])
            print()
        after_pages = [chunk.get("page_number") for chunk in reranked_chunks]

        qa_result = qa_engine.generate_answer(
            question=question,
            retrieved_chunks=reranked_chunks
        )

        print("\nAnswer after reranking")
        print("----------------------")
        print(qa_result["answer"])
        print("Citations:", qa_result["citations"])
        print("\nComparison")
        print("----------")
        print("Before pages:", before_pages)
        print("After pages:", after_pages)
        print("Citations after reranking:", qa_result["citations"])


if __name__ == "__main__":
    main()
