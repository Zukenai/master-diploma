from __future__ import annotations

from app.config.settings import AppConfig
from app.retrieval.base import BaseRetriever
from app.retrieval.dense import DenseRetriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.sparse import SparseRetriever


def build_retriever(config: AppConfig, strategy: str | None = None) -> BaseRetriever:
    selected_strategy = (strategy or config.retrieval.strategy).lower()
    sparse = SparseRetriever(config.paths.sparse_index_path, config.retrieval)
    if selected_strategy == "sparse":
        return sparse

    dense = DenseRetriever(config.paths.processed_corpus_path, config.retrieval)
    if selected_strategy == "dense":
        return dense
    if selected_strategy == "hybrid":
        return HybridRetriever(sparse, dense, config.retrieval)
    raise ValueError(f"Unsupported retrieval strategy: {selected_strategy}")
