from app.config.settings import AppConfig, PathConfig, RerankerConfig, RetrievalConfig, ScoringConfig
from app.ingest.indexer import build_sparse_index
from app.pipeline.assess import PriorArtAssessmentPipeline
from app.schemas.idea import IdeaInput


def test_end_to_end_pipeline_sanity(tmp_path) -> None:
    raw_path = PathConfig().raw_corpus_path
    processed_path = tmp_path / "processed.json"
    index_path = tmp_path / "index.json"
    build_sparse_index(raw_path, processed_path, index_path)

    config = AppConfig(
        retrieval=RetrievalConfig(),
        scoring=ScoringConfig(),
        paths=PathConfig(
            raw_corpus_path=raw_path,
            processed_corpus_path=processed_path,
            sparse_index_path=index_path,
        ),
    )
    pipeline = PriorArtAssessmentPipeline(config)
    idea = IdeaInput.model_validate(
        {
            "idea_id": "IDEA-E2E",
            "title": "Offline prior-art risk module for research ideas",
            "abstract": "The system retrieves local papers, measures overlap risk, and returns a grounded explanation.",
            "keywords": ["offline first", "prior-art risk"],
            "claims": ["estimate overlap risk rather than absolute novelty"],
        }
    )

    result = pipeline.assess(idea)

    assert result.idea_id == "IDEA-E2E"
    assert result.risk_label in {
        "high prior-art risk",
        "medium prior-art risk",
        "low prior-art risk",
    }
    assert "decision_basis" in result.debug


def test_hybrid_pipeline_preserves_json_contract(tmp_path) -> None:
    raw_path = PathConfig().raw_corpus_path
    processed_path = tmp_path / "processed.json"
    index_path = tmp_path / "index.json"
    build_sparse_index(raw_path, processed_path, index_path)

    config = AppConfig(
        retrieval=RetrievalConfig(strategy="hybrid"),
        reranker=RerankerConfig(strategy="overlap"),
        scoring=ScoringConfig(),
        paths=PathConfig(
            raw_corpus_path=raw_path,
            processed_corpus_path=processed_path,
            sparse_index_path=index_path,
        ),
    )
    pipeline = PriorArtAssessmentPipeline(config, retrieval_strategy="hybrid")
    idea = IdeaInput.model_validate(
        {
            "idea_id": "IDEA-HYBRID-E2E",
            "title": "Hybrid retrieval for overlap risk estimation",
            "abstract": "The system combines sparse and dense retrieval, then reranks evidence for explainable overlap risk output.",
            "keywords": ["hybrid retrieval", "overlap risk"],
            "claims": ["combine sparse and dense evidence"],
        }
    )

    result = pipeline.assess(idea)

    assert result.idea_id == "IDEA-HYBRID-E2E"
    assert result.evidence
    assert result.evidence[0].source_retrievers
    assert "retrieval_strategy" in result.debug
