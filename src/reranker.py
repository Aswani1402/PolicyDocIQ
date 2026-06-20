import os
from typing import Any, Dict, List

# PolicyDocIQ uses the PyTorch CrossEncoder path. Prevent Transformers from
# importing an unrelated local TensorFlow/Keras installation.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    """Rerank Qdrant results with a local sentence-transformers CrossEncoder."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu",
    ):
        if not model_name or not model_name.strip():
            raise ValueError("Reranker model_name must not be empty.")

        self.model_name = model_name
        self.device = device

        try:
            self.model = CrossEncoder(model_name, device=device)
        except Exception as error:
            raise RuntimeError(
                f"Could not load CrossEncoder reranker '{model_name}' on {device}."
            ) from error

    def rerank(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return the highest-scoring non-empty chunks after cross-encoder reranking."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Reranker query must be a non-empty string.")

        if not isinstance(retrieved_chunks, list):
            raise TypeError("retrieved_chunks must be a list of dictionaries.")

        if not retrieved_chunks:
            return []

        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")

        valid_chunks: List[Dict[str, Any]] = []
        pairs = []

        for index, chunk in enumerate(retrieved_chunks):
            if not isinstance(chunk, dict):
                raise TypeError(
                    f"Retrieved chunk at index {index} must be a dictionary."
                )

            text = chunk.get("text")
            if not isinstance(text, str) or not text.strip():
                continue

            valid_chunks.append(chunk)
            pairs.append((query.strip(), text.strip()))

        if not valid_chunks:
            return []

        try:
            scores = self.model.predict(
                pairs,
                batch_size=min(16, len(pairs)),
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as error:
            raise RuntimeError(
                f"CrossEncoder reranking failed for {len(valid_chunks)} chunks."
            ) from error

        flat_scores = scores.reshape(-1).tolist()
        if len(flat_scores) != len(valid_chunks):
            raise RuntimeError(
                "CrossEncoder returned a different number of scores than input chunks."
            )

        reranked_chunks = []

        for chunk, rerank_score in zip(valid_chunks, flat_scores):
            updated_chunk = dict(chunk)
            updated_chunk["retrieval_score"] = chunk.get("score")
            updated_chunk["rerank_score"] = float(rerank_score)
            updated_chunk["score"] = float(rerank_score)
            reranked_chunks.append(updated_chunk)

        reranked_chunks.sort(
            key=lambda item: item["rerank_score"],
            reverse=True,
        )

        return reranked_chunks[:top_k]
