from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


class BGEM3Embedder:
    """
    Local embedding model using BAAI/bge-m3.

    This model is stronger than MiniLM and better for dense policy documents.
    """

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu"):
        print(f"Loading embedding model: {model_name}")
        print("This can take a while the first time while BGE-M3 is downloaded or cached.")
        self.model_name = model_name
        self.device = device
        self.model = SentenceTransformer(model_name, device=device)

        self.embedding_dim = self.model.get_embedding_dimension()
        print(f"Embedding dimension: {self.embedding_dim}")

    def encode_texts(
        self,
        texts: List[str],
        batch_size: int = 4,
        normalize_embeddings: bool = True
    ) -> np.ndarray:
        """
        Convert text chunks into embeddings.
        """

        if not texts:
            raise ValueError("No texts provided for embedding.")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=normalize_embeddings
        )

        return np.array(embeddings, dtype="float32")

    def encode_query(self, query: str) -> np.ndarray:
        """
        Convert user query into embedding.
        """

        if not query.strip():
            raise ValueError("Query cannot be empty.")

        embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        )

        return np.array(embedding[0], dtype="float32")
