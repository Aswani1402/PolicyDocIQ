import csv
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Sequence


QUESTION_COLUMNS = [
    "question",
    "category",
    "expected_pages",
    "expected_keywords",
    "notes",
]

RESULT_COLUMNS = [
    "question",
    "category",
    "expected_pages",
    "retrieved_pages",
    "citation_pages",
    "expected_keywords",
    "top_score",
    "answer_found_yes_no",
    "page_hit_yes_no",
    "keyword_hit_yes_no",
    "latency_seconds",
    "answer",
    "notes",
]

NO_ANSWER_PHRASES = (
    "i could not find enough evidence",
    "not enough direct evidence",
)


def _parse_expected_pages(value: str) -> List[int]:
    pages = []

    for part in (value or "").split(";"):
        part = part.strip()
        if not part:
            continue

        try:
            pages.append(int(part))
        except ValueError as error:
            raise ValueError(
                f"Invalid expected page '{part}'. Use semicolon-separated integers."
            ) from error

    return pages


def _parse_expected_keywords(value: str) -> List[str]:
    return [keyword.strip() for keyword in (value or "").split(",") if keyword.strip()]


def _normalize_pages(values: Iterable[Any]) -> List[int]:
    pages = set()

    for value in values:
        if value is None or value == "":
            continue

        try:
            pages.add(int(value))
        except (TypeError, ValueError):
            continue

    return sorted(pages)


def _serialize_pages(pages: Sequence[int]) -> str:
    return ";".join(str(page) for page in pages)


class PolicyDocIQEvaluator:
    """Evaluate the existing retriever and evidence-based QA engine."""

    def __init__(
        self,
        retriever: Any,
        qa_engine: Any,
        top_k: int = 5,
        reranker: Any = None,
        rerank_pool: int = 20,
    ):
        self.retriever = retriever
        self.qa_engine = qa_engine
        self.top_k = top_k
        self.reranker = reranker
        self.rerank_pool = rerank_pool

    def load_questions(self, questions_path: Path) -> List[Dict[str, str]]:
        if not questions_path.exists():
            raise FileNotFoundError(f"Evaluation questions file not found: {questions_path}")

        with questions_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            missing_columns = set(QUESTION_COLUMNS) - set(reader.fieldnames or [])

            if missing_columns:
                raise ValueError(
                    "Evaluation questions file is missing columns: "
                    + ", ".join(sorted(missing_columns))
                )

            questions = [
                {column: (row.get(column) or "").strip() for column in QUESTION_COLUMNS}
                for row in reader
                if (row.get("question") or "").strip()
            ]

        if not questions:
            raise ValueError("Evaluation questions file contains no questions.")

        return questions

    def evaluate_question(self, item: Dict[str, str]) -> Dict[str, Any]:
        question = item["question"]
        expected_pages = _parse_expected_pages(item["expected_pages"])
        expected_keywords = _parse_expected_keywords(item["expected_keywords"])
        started_at = perf_counter()

        try:
            retrieved_chunks = self.retriever.search(
                query=question,
                top_k=self.rerank_pool if self.reranker else self.top_k,
            )
            if self.reranker:
                retrieved_chunks = self.reranker.rerank(
                    query=question,
                    retrieved_chunks=retrieved_chunks,
                    top_k=self.top_k,
                )
            qa_result = self.qa_engine.generate_answer(
                question=question,
                retrieved_chunks=retrieved_chunks,
            )

            answer = str(qa_result.get("answer") or "")
            retrieved_pages = _normalize_pages(
                chunk.get("page_number") for chunk in retrieved_chunks
            )
            citation_pages = _normalize_pages(qa_result.get("citations") or [])
            top_score = (
                float(retrieved_chunks[0].get("score", 0.0))
                if retrieved_chunks
                else 0.0
            )

            answer_lower = answer.casefold()
            answer_found = not any(
                phrase in answer_lower for phrase in NO_ANSWER_PHRASES
            )
            page_hit = bool(
                set(expected_pages) & (set(retrieved_pages) | set(citation_pages))
            )
            keyword_hit = any(
                keyword.casefold() in answer_lower for keyword in expected_keywords
            )
            notes = item["notes"]
        except Exception as error:
            answer = f"Evaluation error: {error}"
            retrieved_pages = []
            citation_pages = []
            top_score = 0.0
            answer_found = False
            page_hit = False
            keyword_hit = False
            notes = " | ".join(
                part for part in [item["notes"], f"Evaluation error: {error}"] if part
            )

        latency_seconds = perf_counter() - started_at

        return {
            "question": question,
            "category": item["category"],
            "expected_pages": item["expected_pages"],
            "retrieved_pages": _serialize_pages(retrieved_pages),
            "citation_pages": _serialize_pages(citation_pages),
            "expected_keywords": item["expected_keywords"],
            "top_score": round(top_score, 4),
            "answer_found_yes_no": "yes" if answer_found else "no",
            "page_hit_yes_no": "yes" if page_hit else "no",
            "keyword_hit_yes_no": "yes" if keyword_hit else "no",
            "latency_seconds": round(latency_seconds, 4),
            "answer": answer,
            "notes": notes,
        }

    def evaluate(self, questions: Sequence[Dict[str, str]]) -> List[Dict[str, Any]]:
        results = []
        total = len(questions)

        for index, item in enumerate(questions, start=1):
            print(f"[{index}/{total}] {item['question']}")
            results.append(self.evaluate_question(item))

        return results

    @staticmethod
    def build_summary(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(results)
        answer_found_count = sum(
            result["answer_found_yes_no"] == "yes" for result in results
        )
        page_hit_count = sum(result["page_hit_yes_no"] == "yes" for result in results)
        keyword_hit_count = sum(
            result["keyword_hit_yes_no"] == "yes" for result in results
        )
        average_latency = (
            sum(float(result["latency_seconds"]) for result in results) / total
            if total
            else 0.0
        )

        def rate(count: int) -> float:
            return round(count / total, 4) if total else 0.0

        return {
            "total_questions": total,
            "answer_found_count": answer_found_count,
            "answer_found_rate": rate(answer_found_count),
            "page_hit_count": page_hit_count,
            "page_hit_rate": rate(page_hit_count),
            "keyword_hit_count": keyword_hit_count,
            "keyword_hit_rate": rate(keyword_hit_count),
            "average_latency_seconds": round(average_latency, 4),
        }

    @staticmethod
    def save_results(results: Sequence[Dict[str, Any]], results_path: Path) -> None:
        results_path.parent.mkdir(parents=True, exist_ok=True)

        with results_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS)
            writer.writeheader()
            writer.writerows(results)

    @staticmethod
    def save_summary(summary: Dict[str, Any], summary_path: Path) -> None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        with summary_path.open("w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2, ensure_ascii=False)
            file.write("\n")
