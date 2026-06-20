import csv
import json
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
from src.evaluator import PolicyDocIQEvaluator, RESULT_COLUMNS
from src.qa_engine import EvidenceBasedQAEngine
from src.reranker import CrossEncoderReranker
from src.retriever import QdrantRAGRetriever


QUESTIONS_PATH = OUTPUTS_DIR / "evaluation_questions.csv"
RESULTS_PATH = OUTPUTS_DIR / "reranker_comparison_results.csv"
SUMMARY_PATH = OUTPUTS_DIR / "reranker_comparison_summary.json"


def main():
    retriever = None

    try:
        retriever = QdrantRAGRetriever(
            collection_name=QDRANT_COLLECTION_NAME,
            qdrant_path=str(QDRANT_PATH),
            embedding_model_name=EMBEDDING_MODEL_NAME,
            device=EMBEDDING_DEVICE,
        )
        qa_engine = EvidenceBasedQAEngine(min_score=0.45)
        reranker = CrossEncoderReranker()

        base_evaluator = PolicyDocIQEvaluator(
            retriever=retriever,
            qa_engine=qa_engine,
            top_k=5,
        )
        questions = base_evaluator.load_questions(QUESTIONS_PATH)

        modes = [
            ("retrieval_only", base_evaluator),
            (
                "retrieval_plus_reranking",
                PolicyDocIQEvaluator(
                    retriever=retriever,
                    qa_engine=qa_engine,
                    top_k=5,
                    reranker=reranker,
                    rerank_pool=20,
                ),
            ),
        ]

        combined_results = []
        summaries = {}

        for mode, evaluator in modes:
            print(f"\nRunning mode: {mode}")
            results = evaluator.evaluate(questions)
            summaries[mode] = evaluator.build_summary(results)

            for result in results:
                combined_results.append({"mode": mode, **result})

        with RESULTS_PATH.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["mode", *RESULT_COLUMNS])
            writer.writeheader()
            writer.writerows(combined_results)

        with SUMMARY_PATH.open("w", encoding="utf-8") as file:
            json.dump(summaries, file, indent=2, ensure_ascii=False)
            file.write("\n")

        print(f"\nComparison results: {RESULTS_PATH}")
        print(f"Comparison summary: {SUMMARY_PATH}")
    finally:
        if retriever is not None:
            retriever.client.close()


if __name__ == "__main__":
    main()
