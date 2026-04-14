from app.config.settings import get_config
from app.schemas.paper import PaperRecord, RetrievedCandidate
from app.scoring.rules import score_candidates


def _candidate(score: float, keyword_terms: list[str]) -> RetrievedCandidate:
    return RetrievedCandidate(
        paper=PaperRecord(
            paper_id=f"P-{score}",
            title="Candidate paper",
            abstract="Abstract text.",
            keywords=["risk"],
            claims=["claim overlap"],
            year=2024,
            venue="TestConf",
        ),
        score=score,
        matched_terms=["risk", "evidence"],
        title_overlap_terms=["risk"],
        keyword_overlap_terms=keyword_terms,
    )


def test_scoring_produces_medium_or_high_risk_for_strong_matches() -> None:
    config = get_config()
    score, label, evidence, debug = score_candidates(
        [_candidate(0.82, ["risk", "evidence"]), _candidate(0.71, ["retrieval"])],
        config.scoring,
    )

    assert score > 0.48
    assert label in {"medium prior-art risk", "high prior-art risk"}
    assert len(evidence) == 2
    assert debug["max_similarity"] == 0.82
