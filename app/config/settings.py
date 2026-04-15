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
    high_risk_score: float = 0.8
    medium_risk_score: float = 0.46
    strong_similarity_threshold: float = 0.70
    moderate_similarity_threshold: float = 0.45
    keyword_overlap_weight: float = 0.14
    max_similarity_weight: float = 0.34
    avg_top_similarity_weight: float = 0.18
    count_above_threshold_weight: float = 0.08
    claim_overlap_weight: float = 0.16
    title_overlap_weight: float = 0.10
    facet_coverage_weight: float = 0.08
    multi_source_weight: float = 0.06
    evidence_count_weight: float = 0.06
    weak_support_penalty_weight: float = 0.10
    weak_support_threshold: float = 0.34
    strong_support_weight: float = 0.12
    shallow_support_penalty_weight: float = 0.22
    lexical_only_penalty_weight: float = 0.14
    strong_support_overlap_threshold: int = 3
    shallow_support_overlap_threshold: int = 1


class EvaluationConfig(BaseModel):
    default_modes: list[str] = Field(default_factory=lambda: ["sparse", "dense", "hybrid"])


class PathConfig(BaseModel):
    raw_corpus_path: Path = Path("data/raw/sample_corpus.json")
    processed_corpus_path: Path = Path("data/processed/normalized_corpus.json")
    sparse_index_path: Path = Path("data/indexes/sparse_index.json")
    curated_manifest_path: Path = Path("data/provenance/curated_corpus_manifest.json")
    curated_snapshot_path: Path = Path("data/raw/curated_openalex_snapshot.json")
    curated_raw_corpus_path: Path = Path("data/raw/curated_scholarly_corpus.json")
    curated_processed_corpus_path: Path = Path("data/processed/curated_normalized_corpus.json")
    curated_sparse_index_path: Path = Path("data/indexes/curated_sparse_index.json")
    curated_provenance_path: Path = Path("data/provenance/curated_corpus_provenance.json")
    manual_eval_dir: Path = Path("scripts/manual_eval")
    curated_eval_dir: Path = Path("scripts/curated_eval")
    manual_eval_expectations_path: Path = Path("data/eval/manual_eval_expectations.json")
    manual_eval_report_path: Path = Path("data/processed/manual_eval_report.json")
    curated_eval_expectations_path: Path = Path("data/eval/curated_experiment_expectations.json")
    curated_experiment_report_path: Path = Path("data/processed/curated_experiment_report.json")
    curated_experiment_notes_path: Path = Path("data/processed/curated_experiment_notes.md")
    evaluation_annotation_protocol_path: Path = Path("docs/evaluation_annotation_protocol.md")


class AppConfig(BaseModel):
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    paths: PathConfig = Field(default_factory=PathConfig)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()


def with_corpus_paths(config: AppConfig, corpus_name: str) -> AppConfig:
    corpus = corpus_name.lower()
    if corpus == "sample":
        return config
    if corpus == "curated":
        updated_paths = config.paths.model_copy(
            update={
                "raw_corpus_path": config.paths.curated_raw_corpus_path,
                "processed_corpus_path": config.paths.curated_processed_corpus_path,
                "sparse_index_path": config.paths.curated_sparse_index_path,
            }
        )
        return config.model_copy(deep=True, update={"paths": updated_paths})
    raise ValueError(f"Unsupported corpus name: {corpus_name}")
