import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    EMBEDDING_DEVICE,
    EMBEDDING_MODEL_NAME,
    OUTPUTS_DIR,
    QDRANT_COLLECTION_NAME,
    QDRANT_PATH,
)
from src.evaluator import PolicyDocIQEvaluator
from src.qa_engine import EvidenceBasedQAEngine
from src.retriever import QdrantRAGRetriever


QUESTIONS_PATH = OUTPUTS_DIR / "evaluation_questions.csv"
RESULTS_PATH = OUTPUTS_DIR / "evaluation_results.csv"
SUMMARY_PATH = OUTPUTS_DIR / "evaluation_summary.json"
INDEX_REQUIRED_MESSAGE = "Run scripts/02_index_qdrant.py first."


def print_summary(summary):
    print("\nPolicyDocIQ Evaluation Summary")
    print("------------------------------")
    print(f"Total questions: {summary['total_questions']}")
    print(f"Answer found rate: {summary['answer_found_rate']:.1%}")
    print(f"Page hit rate: {summary['page_hit_rate']:.1%}")
    print(f"Keyword hit rate: {summary['keyword_hit_rate']:.1%}")
    print(f"Average latency: {summary['average_latency_seconds']:.4f} seconds")
    print(f"\nDetailed results: {RESULTS_PATH}")
    print(f"Summary JSON: {SUMMARY_PATH}")


def main():
    if not QDRANT_PATH.exists():
        raise SystemExit(
            f"Qdrant DB not found at {QDRANT_PATH}. {INDEX_REQUIRED_MESSAGE}"
        )

    retriever = None

    try:
        retriever = QdrantRAGRetriever(
            collection_name=QDRANT_COLLECTION_NAME,
            qdrant_path=str(QDRANT_PATH),
            embedding_model_name=EMBEDDING_MODEL_NAME,
            device=EMBEDDING_DEVICE,
        )

        if not retriever.collection_exists():
            raise SystemExit(
                f"Qdrant collection '{QDRANT_COLLECTION_NAME}' was not found. "
                f"{INDEX_REQUIRED_MESSAGE}"
            )

        evaluator = PolicyDocIQEvaluator(
            retriever=retriever,
            qa_engine=EvidenceBasedQAEngine(min_score=0.45),
            top_k=5,
        )
        questions = evaluator.load_questions(QUESTIONS_PATH)

        print("PolicyDocIQ RAG Evaluation")
        print(f"Questions: {len(questions)}")
        print(f"Collection: {QDRANT_COLLECTION_NAME}")
        print(f"Indexed chunks: {retriever.point_count()}")
        print("This workflow does not extract PDFs or re-index Qdrant.\n")

        results = evaluator.evaluate(questions)
        summary = evaluator.build_summary(results)
        evaluator.save_results(results, RESULTS_PATH)
        evaluator.save_summary(summary, SUMMARY_PATH)
        print_summary(summary)
    except RuntimeError as error:
        raise SystemExit(
            f"{error}\nStop the FastAPI process before evaluation because local "
            "Qdrant allows one process at a time."
        ) from error
    finally:
        if retriever is not None:
            retriever.client.close()


if __name__ == "__main__":
    main()
