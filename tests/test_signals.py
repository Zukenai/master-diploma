from app.retrieval.signals import build_overlap_metadata
from app.schemas.idea import IdeaInput
from app.schemas.paper import PaperRecord


def test_overlap_metadata_includes_claim_and_facet_signals() -> None:
    idea = IdeaInput.model_validate(
        {
            "idea_id": "IDEA-SIGNALS",
            "title": "Claim-aware novelty risk screening",
            "abstract": "Use claim overlap and evidence facets to screen novelty risk.",
            "keywords": ["novelty risk", "claim-aware retrieval"],
            "claims": ["use claim terms as signals"],
        }
    )
    paper = PaperRecord.model_validate(
        {
            "paper_id": "P-SIGNALS",
            "title": "Claim-Aware Similarity Signals for Patent Prior Art Screening",
            "abstract": "Claim terms and title overlap support transparent screening.",
            "keywords": ["claim-aware retrieval", "novelty risk"],
            "claims": ["use claim terms as retrieval signals"],
            "year": 2024,
            "venue": "TestConf",
        }
    )

    metadata = build_overlap_metadata(idea, paper)

    assert metadata["claim_overlap_count"] >= 1
    assert metadata["facet_overlap_count"] >= 2
