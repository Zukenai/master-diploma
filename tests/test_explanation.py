from app.explanation.templates import build_explanation
from app.schemas.assessment import EvidenceItem


def test_explanation_mentions_risk_and_evidence_titles() -> None:
    explanation = build_explanation(
        "medium prior-art risk",
        0.57,
        [
            EvidenceItem(
                paper_id="P1",
                title="Assessing Novelty Risk in Research Proposals with Literature Evidence",
                score=0.7,
                overlap_signals={"matched_terms": ["risk", "evidence"]},
                rationale="test",
            )
        ],
    )

    assert "medium prior-art risk" in explanation
    assert "Novelty Risk" in explanation
