import re
from typing import List, Dict, Any


class EvidenceBasedQAEngine:
    """
    Citation-backed extractive QA engine.

    No external API.
    No hallucination.
    Answers only from retrieved document evidence.
    """

    def __init__(self, min_score: float = 0.45):
        self.min_score = min_score

    def split_into_sentences(self, text: str) -> List[str]:
        if not text:
            return []

        text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)

        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def detect_question_intent(self, question: str) -> str:
        q = question.lower()

        if any(term in q for term in ["gdp", "growth", "projected growth"]):
            return "growth"

        if any(term in q for term in ["risk", "risks", "outlook"]):
            return "risks"

        if any(term in q for term in ["vat", "value-added tax", "tax"]):
            return "vat"

        if any(term in q for term in ["bank", "banking", "financial sector", "npl", "capital adequacy"]):
            return "banking"

        return "general"

    def get_intent_keywords(self, intent: str) -> List[str]:
        keyword_map = {
            "growth": [
                "gdp", "growth", "projected", "projection", "2024", "2025",
                "real gdp", "medium-term", "lng", "tourism", "public investment"
            ],
            "risks": [
                "risk", "risks", "downside", "outlook", "slowdown",
                "volatility", "geopolitical", "commodity", "fragmentation",
                "global growth", "financial conditions"
            ],
            "vat": [
                "vat", "value-added tax", "tax", "revenue", "broad-based",
                "gcc treaty", "5 percent", "implementation"
            ],
            "banking": [
                "banking", "banks", "bank", "capitalized", "capital adequacy",
                "liquid", "liquidity", "npl", "credit", "net interest margin",
                "financial sector"
            ],
            "general": []
        }

        return keyword_map.get(intent, [])

    def get_query_keywords(self, question: str) -> List[str]:
        stopwords = {
            "what", "is", "are", "the", "for", "and", "to", "of", "in", "on",
            "does", "say", "about", "summarize", "qatar", "report", "with",
            "condition", "projected", "main"
        }

        words = re.findall(r"[A-Za-z0-9]+", question.lower())
        return [word for word in words if word not in stopwords and len(word) > 2]

    def is_noisy_sentence(self, sentence: str) -> bool:
        if not sentence:
            return True

        words = sentence.split()

        if len(words) < 6:
            return True

        if len(words) > 80:
            return True

        number_count = len(re.findall(r"\d+(\.\d+)?", sentence))
        if number_count > 12:
            return True

        symbol_count = sentence.count("%") + sentence.count("…") + sentence.count("/")
        if symbol_count > 8:
            return True

        noisy_phrases = [
            "selected macroeconomic indicators",
            "summary of central government finance",
            "vulnerability indicators",
            "sources:",
            "memorandum items",
            "table 6",
            "table 1"
        ]

        sentence_lower = sentence.lower()

        if any(phrase in sentence_lower for phrase in noisy_phrases) and len(words) > 30:
            return True

        return False

    def sentence_matches_intent(self, sentence: str, intent_keywords: List[str]) -> bool:
        if not intent_keywords:
            return True

        sentence_lower = sentence.lower()

        return any(keyword in sentence_lower for keyword in intent_keywords)

    def rank_sentences(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        max_sentences: int = 4
    ) -> List[Dict[str, Any]]:

        intent = self.detect_question_intent(question)
        query_keywords = self.get_query_keywords(question)
        intent_keywords = self.get_intent_keywords(intent)

        ranked_sentences = []
        seen_sentences = set()

        for chunk in retrieved_chunks:
            text = chunk.get("text", "")
            page_number = chunk.get("page_number")
            score = float(chunk.get("score", 0.0))

            sentences = self.split_into_sentences(text)

            for sentence in sentences:
                if self.is_noisy_sentence(sentence):
                    continue

                normalized = sentence.lower().strip()

                if normalized in seen_sentences:
                    continue

                seen_sentences.add(normalized)

                # Important fix:
                # Do not include unrelated high-score sentences.
                if not self.sentence_matches_intent(sentence, intent_keywords):
                    continue

                sentence_lower = sentence.lower()

                query_hits = sum(1 for keyword in query_keywords if keyword in sentence_lower)
                intent_hits = sum(1 for keyword in intent_keywords if keyword in sentence_lower)

                if query_hits == 0 and intent_hits == 0:
                    continue

                final_score = score + query_hits + (intent_hits * 1.5)

                ranked_sentences.append(
                    {
                        "sentence": sentence,
                        "page_number": page_number,
                        "retrieval_score": score,
                        "query_hits": query_hits,
                        "intent_hits": intent_hits,
                        "final_score": final_score
                    }
                )

        ranked_sentences = sorted(
            ranked_sentences,
            key=lambda item: item["final_score"],
            reverse=True
        )

        return ranked_sentences[:max_sentences]

    def generate_answer(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        if not retrieved_chunks:
            return {
                "answer": "I could not find enough evidence in the document.",
                "citations": [],
                "evidence": []
            }

        top_chunk = retrieved_chunks[0]
        confidence_score = top_chunk.get("retrieval_score")
        if confidence_score is None:
            confidence_score = top_chunk.get("score", 0.0)

        if float(confidence_score) < self.min_score:
            return {
                "answer": "I could not find enough evidence in the document.",
                "citations": [],
                "evidence": retrieved_chunks
            }

        selected_sentences = self.rank_sentences(
            question=question,
            retrieved_chunks=retrieved_chunks,
            max_sentences=4
        )

        if not selected_sentences:
            return {
                "answer": "I found related sections, but not enough direct evidence to answer confidently.",
                "citations": [],
                "evidence": retrieved_chunks
            }

        answer_lines = [
            f"- {item['sentence']} [Page {item['page_number']}]"
            for item in selected_sentences
        ]

        citations = sorted(list({item["page_number"] for item in selected_sentences}))

        answer = "Based on the retrieved IMF report evidence:\n\n" + "\n".join(answer_lines)

        return {
            "answer": answer,
            "citations": citations,
            "evidence": retrieved_chunks
        }
