from __future__ import annotations

from statistics import mean

from app.config.settings import ScoringConfig
from app.schemas.assessment import EvidenceItem
from app.schemas.paper import RetrievedCandidate


def _risk_label(score: float, config: ScoringConfig) -> str:
    if score >= config.high_risk_score:
        return "high prior-art risk"
    if score >= config.medium_risk_score:
        return "medium prior-art risk"
    return "low prior-art risk"


def score_candidates(
    candidates: list[RetrievedCandidate],
    config: ScoringConfig,
) -> tuple[float, str, list[EvidenceItem], dict[str, float | int | str | list[str]]]:
    if not candidates:
        debug = {
            "max_similarity": 0.0,
            "avg_top_similarity": 0.0,
            "count_above_threshold": 0,
            "aggregate_keyword_overlap": 0,
            "decision_basis": "no_retrieved_candidates",
        }
        return 0.0, "low prior-art risk", [], debug

    similarities = [candidate.score for candidate in candidates]
    max_similarity = max(similarities)
    avg_top_similarity = mean(similarities[: min(3, len(similarities))])
    count_above_threshold = sum(
        1 for score in similarities if score >= config.moderate_similarity_threshold
    )
    aggregate_keyword_overlap = sum(len(candidate.keyword_overlap_terms) for candidate in candidates[:3])

    count_ratio = min(count_above_threshold / 3, 1.0)
    keyword_ratio = min(aggregate_keyword_overlap / 6, 1.0)
    risk_score = (
        max_similarity * config.max_similarity_weight
        + avg_top_similarity * config.avg_top_similarity_weight
        + count_ratio * config.count_above_threshold_weight
        + keyword_ratio * config.keyword_overlap_weight
    )
    risk_score = round(min(risk_score, 1.0), 4)
    label = _risk_label(risk_score, config)

    evidence = [
        EvidenceItem(
            paper_id=candidate.paper.paper_id,
            title=candidate.paper.title,
            score=candidate.score,
            overlap_signals={
                "matched_terms": candidate.matched_terms,
                "title_overlap_terms": candidate.title_overlap_terms,
                "keyword_overlap_terms": candidate.keyword_overlap_terms,
            },
            rationale=(
                f"Retrieved with score {candidate.score:.3f}; "
                f"title overlap={len(candidate.title_overlap_terms)}, "
                f"keyword overlap={len(candidate.keyword_overlap_terms)}."
            ),
        )
        for candidate in candidates[:3]
    ]

    debug = {
        "max_similarity": round(max_similarity, 4),
        "avg_top_similarity": round(avg_top_similarity, 4),
        "count_above_threshold": count_above_threshold,
        "aggregate_keyword_overlap": aggregate_keyword_overlap,
        "decision_basis": (
            "high_overlap_signals"
            if label == "high prior-art risk"
            else "moderate_overlap_signals"
            if label == "medium prior-art risk"
            else "limited_overlap_signals"
        ),
    }
    return risk_score, label, evidence, debug
