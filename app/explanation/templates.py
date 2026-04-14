from __future__ import annotations

from app.schemas.assessment import EvidenceItem


def build_explanation(
    risk_label: str,
    risk_score: float,
    evidence: list[EvidenceItem],
) -> str:
    if not evidence:
        return (
            "The current corpus did not return sufficiently similar papers, "
            "so the idea is assessed as low prior-art risk relative to this baseline."
        )

    top_titles = ", ".join(item.title for item in evidence[:2])
    sources = sorted({source for item in evidence for source in item.source_retrievers})
    overlap_summary = "; ".join(
        f"{item.paper_id}: matched {len(item.overlap_signals.get('matched_terms', []))} terms"
        for item in evidence[:3]
    )
    return (
        f"The idea is assessed as {risk_label} with score {risk_score:.2f}. "
        f"Top overlapping papers include {top_titles}. "
        f"Evidence was gathered via {', '.join(sources) if sources else 'the active retriever'} retrieval. "
        f"Observed overlap signals: {overlap_summary}. "
        "This verdict is evidence-grounded and limited to the local indexed corpus."
    )
