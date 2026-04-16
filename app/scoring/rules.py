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
            "aggregate_claim_overlap": 0,
            "aggregate_title_overlap": 0,
            "facet_coverage": 0.0,
            "multi_source_ratio": 0.0,
            "strong_support_count": 0,
            "shallow_support_count": 0,
            "lexical_only_count": 0,
            "weak_support_count": 0,
            "evidence_sources": [],
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
    aggregate_claim_overlap = sum(len(candidate.claim_overlap_terms) for candidate in candidates[:3])
    aggregate_title_overlap = sum(len(candidate.title_overlap_terms) for candidate in candidates[:3])
    overlap_totals = [
        len(candidate.title_overlap_terms)
        + len(candidate.keyword_overlap_terms)
        + len(candidate.claim_overlap_terms)
        for candidate in candidates[:3]
    ]
    facet_coverages = [
        sum(
            1
            for overlap_terms in [
                candidate.title_overlap_terms,
                candidate.keyword_overlap_terms,
                candidate.claim_overlap_terms,
            ]
            if overlap_terms
        )
        / 3
        for candidate in candidates[:3]
    ]
    facet_coverage = mean(facet_coverages) if facet_coverages else 0.0
    evidence_count_ratio = min(len(candidates[:3]) / 3, 1.0)
    multi_source_ratio = sum(
        1
        for candidate in candidates[:3]
        if len([source for source in candidate.source_retrievers if source != "hybrid"]) >= 2
    ) / max(min(3, len(candidates)), 1)
    strong_support_count = sum(
        1
        for overlap_total in overlap_totals
        if overlap_total >= config.strong_support_overlap_threshold
    )
    shallow_support_count = sum(
        1
        for overlap_total in overlap_totals
        if overlap_total <= config.shallow_support_overlap_threshold
    )
    lexical_only_count = sum(
        1
        for candidate in candidates[:3]
        if (
            len(candidate.keyword_overlap_terms) > 0
            and len(candidate.title_overlap_terms) == 0
            and len(candidate.claim_overlap_terms) == 0
        )
    )
    weak_support_count = sum(
        1
        for candidate in candidates[:3]
        if (
            len(candidate.claim_overlap_terms) == 0
            and len(candidate.title_overlap_terms) == 0
            and len(candidate.keyword_overlap_terms) == 0
        )
        or (
            candidate.score < config.weak_support_threshold
            and len(candidate.claim_overlap_terms) == 0
            and len(candidate.title_overlap_terms) == 0
        )
    )

    count_ratio = min(count_above_threshold / 3, 1.0)
    keyword_ratio = min(aggregate_keyword_overlap / 6, 1.0)
    claim_ratio = min(aggregate_claim_overlap / 4, 1.0)
    title_ratio = min(aggregate_title_overlap / 4, 1.0)
    strong_support_ratio = min(strong_support_count / 3, 1.0)
    shallow_support_penalty = min(shallow_support_count / 3, 1.0)
    lexical_only_penalty = min(lexical_only_count / 3, 1.0)
    weak_support_penalty = min(weak_support_count / 3, 1.0)
    risk_score = (
        max_similarity * config.max_similarity_weight
        + avg_top_similarity * config.avg_top_similarity_weight
        + count_ratio * config.count_above_threshold_weight
        + keyword_ratio * config.keyword_overlap_weight
        + claim_ratio * config.claim_overlap_weight
        + title_ratio * config.title_overlap_weight
        + facet_coverage * config.facet_coverage_weight
        + multi_source_ratio * config.multi_source_weight
        + evidence_count_ratio * config.evidence_count_weight
        + strong_support_ratio * config.strong_support_weight
        - shallow_support_penalty * config.shallow_support_penalty_weight
        - lexical_only_penalty * config.lexical_only_penalty_weight
        - weak_support_penalty * config.weak_support_penalty_weight
    )
    risk_score = round(min(max(risk_score, 0.0), 1.0), 4)
    label = _risk_label(risk_score, config)
    limited_evidence_high_guard_applied = False
    if (
        label == "high prior-art risk"
        and evidence_count_ratio < 1.0
        and avg_top_similarity < config.high_risk_limited_evidence_min_avg_similarity
    ):
        # Guardrail for compact borderline cases: two admissible pieces of evidence alone
        # should not escalate to high risk unless their aggregate similarity is near-saturated.
        label = "medium prior-art risk"
        limited_evidence_high_guard_applied = True

    evidence = [
        EvidenceItem(
            paper_id=candidate.paper.paper_id,
            title=candidate.paper.title,
            score=candidate.score,
            source_retrievers=candidate.source_retrievers,
            sparse_score=candidate.sparse_score,
            dense_score=candidate.dense_score,
            fused_score=candidate.fused_score,
            rerank_score=candidate.rerank_score,
            overlap_signals={
                "matched_terms": candidate.matched_terms,
                "title_overlap_terms": candidate.title_overlap_terms,
                "keyword_overlap_terms": candidate.keyword_overlap_terms,
                "claim_overlap_terms": candidate.claim_overlap_terms,
                "source_retrievers": candidate.source_retrievers,
                "debug_signals": candidate.debug_signals,
            },
            rationale=(
                f"Retrieved with score {candidate.score:.3f}; "
                f"sources={','.join(candidate.source_retrievers)}; "
                f"title overlap={len(candidate.title_overlap_terms)}, "
                f"keyword overlap={len(candidate.keyword_overlap_terms)}, "
                f"claim overlap={len(candidate.claim_overlap_terms)}."
            ),
        )
        for candidate in candidates[:3]
    ]

    debug = {
        "max_similarity": round(max_similarity, 4),
        "avg_top_similarity": round(avg_top_similarity, 4),
        "count_above_threshold": count_above_threshold,
        "aggregate_keyword_overlap": aggregate_keyword_overlap,
        "aggregate_claim_overlap": aggregate_claim_overlap,
        "aggregate_title_overlap": aggregate_title_overlap,
        "facet_coverage": round(facet_coverage, 4),
        "evidence_count_ratio": round(evidence_count_ratio, 4),
        "multi_source_ratio": round(multi_source_ratio, 4),
        "strong_support_count": strong_support_count,
        "shallow_support_count": shallow_support_count,
        "lexical_only_count": lexical_only_count,
        "weak_support_count": weak_support_count,
        "limited_evidence_high_guard_applied": limited_evidence_high_guard_applied,
        "evidence_sources": sorted(
            {
                source
                for candidate in candidates[:3]
                for source in candidate.source_retrievers
            }
        ),
        "decision_basis": (
            "high_overlap_signals"
            if label == "high prior-art risk"
            else "moderate_overlap_signals"
            if label == "medium prior-art risk"
            else "limited_overlap_signals"
        ),
    }
    return risk_score, label, evidence, debug
