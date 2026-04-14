from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class RetrievalConfig(BaseModel):
    strategy: str = "sparse"
    top_k: int = 5
    min_score: float = 0.05
    dense_min_score: float = 0.02
    title_boost: float = 1.2
    keyword_boost: float = 1.1
    candidate_pool_size: int = 8
    fusion_constant: int = 60
    dense_embedding_dims: int = 8


class RerankerConfig(BaseModel):
    strategy: str = "overlap"
    title_overlap_bonus: float = 0.02
    keyword_overlap_bonus: float = 0.015
    matched_term_bonus: float = 0.005
    max_bonus: float = 0.08


class ScoringConfig(BaseModel):
    high_risk_score: float = 0.74
    medium_risk_score: float = 0.48
    strong_similarity_threshold: float = 0.70
    moderate_similarity_threshold: float = 0.45
    keyword_overlap_weight: float = 0.20
    max_similarity_weight: float = 0.45
    avg_top_similarity_weight: float = 0.25
    count_above_threshold_weight: float = 0.10


class PathConfig(BaseModel):
    raw_corpus_path: Path = Path("data/raw/sample_corpus.json")
    processed_corpus_path: Path = Path("data/processed/normalized_corpus.json")
    sparse_index_path: Path = Path("data/indexes/sparse_index.json")


class AppConfig(BaseModel):
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    paths: PathConfig = Field(default_factory=PathConfig)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
