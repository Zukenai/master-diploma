from app.config.settings import AppConfig, PathConfig, RetrievalConfig, ScoringConfig
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
