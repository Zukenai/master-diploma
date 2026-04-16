from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from app.config.settings import AppConfig, with_corpus_paths
from app.explanation.templates import build_explanation
from app.pipeline.assess import PriorArtAssessmentPipeline
from app.rerank.base import NoOpReranker, OverlapReranker
from app.retrieval.signals import build_overlap_metadata
from app.schemas.idea import IdeaInput
from app.schemas.paper import PaperRecord, RetrievedCandidate
from app.scoring.rules import score_candidates

LABELS = ["low prior-art risk", "medium prior-art risk", "high prior-art risk"]
LABEL_TO_ORDINAL = {label: index for index, label in enumerate(LABELS)}
FAILURE_TYPES = [
    "ok",
    "retrieval_miss",
    "oracle_wrong",
    "lexical_overfire",
    "borderline_underfire",
    "near_duplicate_miss",
    "insufficient_evidence_high_verdict",
]


def _load_expectations(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["case_id"]: item for item in payload}


def _load_curated_corpus(path: Path) -> dict[str, PaperRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        item["paper_id"]: PaperRecord.model_validate(item)
        for item in payload
    }


def _load_curated_cases(path: Path) -> list[IdeaInput]:
    return [
        IdeaInput.model_validate_json(case_path.read_text(encoding="utf-8"))
        for case_path in sorted(path.glob("*.json"))
    ]


def _truth_label(expectation: dict[str, object]) -> str:
    return str(
        expectation.get(
            "adjudicated_label",
            expectation.get("expected_risk", "low prior-art risk"),
        )
    )


def _case_type(expectation: dict[str, object]) -> str:
    return str(expectation.get("case_type", expectation.get("review_case_type", "unspecified")))


def _label_distribution(items: list[str]) -> dict[str, int]:
    counts = {label: 0 for label in LABELS}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


def _corpus_summary(config: AppConfig) -> dict[str, object]:
    records = json.loads(config.paths.curated_raw_corpus_path.read_text(encoding="utf-8"))
    years = [record["year"] for record in records]
    venues: dict[str, int] = {}
    for record in records:
        venues[record["venue"]] = venues.get(record["venue"], 0) + 1
    return {
        "document_count": len(records),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "venues": venues,
        "raw_corpus_path": str(config.paths.curated_raw_corpus_path),
        "provenance_path": str(config.paths.curated_provenance_path),
    }


def _precision_recall_f1(
    truth: list[str],
    predicted: list[str],
) -> dict[str, object]:
    confusion: dict[str, dict[str, int]] = {
        expected: {actual: 0 for actual in LABELS}
        for expected in LABELS
    }
    for expected, actual in zip(truth, predicted, strict=True):
        confusion[expected][actual] += 1

    per_label: dict[str, dict[str, float | int]] = {}
    f1_values: list[float] = []
    for label in LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[expected][label] for expected in LABELS if expected != label)
        fn = sum(confusion[label][actual] for actual in LABELS if actual != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_label[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(confusion[label].values()),
        }
        f1_values.append(f1)

    accuracy = sum(1 for expected, actual in zip(truth, predicted, strict=True) if expected == actual) / max(len(truth), 1)
    mean_ordinal_error = (
        sum(abs(LABEL_TO_ORDINAL[expected] - LABEL_TO_ORDINAL[actual]) for expected, actual in zip(truth, predicted, strict=True))
        / max(len(truth), 1)
    )
    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(sum(f1_values) / len(LABELS), 4),
        "mean_ordinal_error": round(mean_ordinal_error, 4),
        "per_label": per_label,
        "confusion": confusion,
        "adjacent_confusion_summary": {
            "low_to_medium": confusion["low prior-art risk"]["medium prior-art risk"],
            "medium_to_low": confusion["medium prior-art risk"]["low prior-art risk"],
            "medium_to_high": confusion["medium prior-art risk"]["high prior-art risk"],
            "high_to_medium": confusion["high prior-art risk"]["medium prior-art risk"],
        },
        "predicted_label_distribution": _label_distribution(predicted),
        "expected_label_distribution": _label_distribution(truth),
    }


def _case_type_breakdown(
    items: list[dict[str, object]],
    match_field: str,
) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in items:
        grouped.setdefault(str(item["case_type"]), []).append(item)

    breakdown: dict[str, dict[str, float | int]] = {}
    for case_type, case_items in grouped.items():
        match_count = sum(1 for item in case_items if item.get(match_field))
        breakdown[case_type] = {
            "case_count": len(case_items),
            "match_count": match_count,
            "match_rate": round(match_count / len(case_items), 4) if case_items else 0.0,
        }
    return breakdown


def _case_type_distribution(expectations: dict[str, dict[str, object]]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for item in expectations.values():
        case_type = _case_type(item)
        distribution[case_type] = distribution.get(case_type, 0) + 1
    return distribution


def _review_adjudication_summary(expectations: dict[str, dict[str, object]]) -> dict[str, object]:
    label_changes = [
        case_id
        for case_id, item in expectations.items()
        if item.get("initial_label") != item.get("review_label")
    ]
    case_type_changes = [
        case_id
        for case_id, item in expectations.items()
        if item.get("initial_case_type", item.get("case_type")) != item.get("review_case_type", item.get("case_type"))
    ]
    sufficiency_changes = [
        case_id
        for case_id, item in expectations.items()
        if item.get("initial_oracle_evidence_sufficiency") != item.get("review_oracle_evidence_sufficiency")
    ]
    adjudication_label_changes = [
        case_id
        for case_id, item in expectations.items()
        if item.get("review_label", item.get("expected_risk")) != _truth_label(item)
    ]
    return {
        "label_changes_on_review": len(label_changes),
        "label_change_case_ids": label_changes,
        "case_type_changes_on_review": len(case_type_changes),
        "case_type_change_case_ids": case_type_changes,
        "oracle_evidence_sufficiency_changes_on_review": len(sufficiency_changes),
        "oracle_evidence_sufficiency_change_case_ids": sufficiency_changes,
        "adjudicated_label_changes_from_review": len(adjudication_label_changes),
        "adjudicated_label_change_case_ids": adjudication_label_changes,
    }


def _support_score(overlap_metadata: dict[str, list[str] | int]) -> float:
    matched_term_count = int(overlap_metadata["matched_term_count"])
    title_overlap_count = int(overlap_metadata["title_overlap_count"])
    keyword_overlap_count = int(overlap_metadata["keyword_overlap_count"])
    claim_overlap_count = int(overlap_metadata["claim_overlap_count"])
    facet_overlap_count = int(overlap_metadata["facet_overlap_count"])
    support_score = (
        0.28
        + min(matched_term_count, 6) * 0.04
        + title_overlap_count * 0.06
        + keyword_overlap_count * 0.04
        + claim_overlap_count * 0.07
        + facet_overlap_count * 0.05
    )
    return round(min(support_score, 0.98), 4)


def _evidence_strength(overlap_metadata: dict[str, list[str] | int]) -> str:
    title_overlap_count = int(overlap_metadata["title_overlap_count"])
    keyword_overlap_count = int(overlap_metadata["keyword_overlap_count"])
    claim_overlap_count = int(overlap_metadata["claim_overlap_count"])
    facet_overlap_count = int(overlap_metadata["facet_overlap_count"])

    if claim_overlap_count > 0 and title_overlap_count > 0:
        return "direct overlap"
    if facet_overlap_count >= 2:
        return "multi-facet overlap"
    if claim_overlap_count > 0 or title_overlap_count > 0:
        return "partial overlap"
    if keyword_overlap_count > 0:
        return "lexical-only similarity"
    return "adjacent-but-distinct similarity"


def _filter_admissible_ids(
    paper_ids: list[str],
    cutoff_year: int,
    corpus_map: dict[str, PaperRecord],
) -> tuple[list[str], list[str], list[str]]:
    admissible: list[str] = []
    inadmissible: list[str] = []
    missing: list[str] = []
    for paper_id in paper_ids:
        paper = corpus_map.get(paper_id)
        if paper is None:
            missing.append(paper_id)
            continue
        if paper.year <= cutoff_year:
            admissible.append(paper_id)
        else:
            inadmissible.append(paper_id)
    return admissible, inadmissible, missing


def _filter_admissible_candidates(
    candidates: list[RetrievedCandidate],
    cutoff_year: int,
) -> tuple[list[RetrievedCandidate], list[str]]:
    admissible: list[RetrievedCandidate] = []
    inadmissible_ids: list[str] = []
    for candidate in candidates:
        if candidate.paper.year <= cutoff_year:
            admissible.append(candidate)
        else:
            inadmissible_ids.append(candidate.paper.paper_id)
    return admissible, inadmissible_ids


def _oracle_candidates(
    idea: IdeaInput,
    oracle_paper_ids: list[str],
    corpus_map: dict[str, PaperRecord],
) -> tuple[list[RetrievedCandidate], list[str]]:
    candidates: list[RetrievedCandidate] = []
    missing_ids: list[str] = []
    for paper_id in oracle_paper_ids:
        paper = corpus_map.get(paper_id)
        if paper is None:
            missing_ids.append(paper_id)
            continue
        overlap_metadata = build_overlap_metadata(idea, paper)
        support_score = _support_score(overlap_metadata)
        evidence_strength = _evidence_strength(overlap_metadata)
        candidates.append(
            RetrievedCandidate(
                paper=paper,
                score=support_score,
                source_retrievers=["oracle"],
                fused_score=support_score,
                matched_terms=overlap_metadata["matched_terms"],
                title_overlap_terms=overlap_metadata["title_overlap_terms"],
                keyword_overlap_terms=overlap_metadata["keyword_overlap_terms"],
                claim_overlap_terms=overlap_metadata["claim_overlap_terms"],
                debug_signals={
                    "retriever": "oracle",
                    "evidence_strength": evidence_strength,
                    "matched_term_count": overlap_metadata["matched_term_count"],
                    "title_overlap_count": overlap_metadata["title_overlap_count"],
                    "keyword_overlap_count": overlap_metadata["keyword_overlap_count"],
                    "claim_overlap_count": overlap_metadata["claim_overlap_count"],
                    "facet_overlap_count": overlap_metadata["facet_overlap_count"],
                },
            )
        )
    return candidates, missing_ids


def _shared_case_outcomes(cases: list[dict[str, object]], match_field: str, case_type: str | None = None, expected_label: str | None = None) -> dict[str, float | int]:
    filtered = [
        case
        for case in cases
        if (case_type is None or case.get("case_type") == case_type)
        and (expected_label is None or case.get("expected_risk") == expected_label)
    ]
    match_count = sum(1 for case in filtered if case.get(match_field))
    return {
        "case_count": len(filtered),
        "match_count": match_count,
        "match_rate": round(match_count / len(filtered), 4) if filtered else 0.0,
    }


def _oracle_lookup_from_report(report: dict[str, object]) -> dict[str, dict[str, object]]:
    oracle_section = report.get("oracle_verdict_evaluation", {})
    return {case["case_id"]: case for case in oracle_section.get("cases", [])}


def _end_to_end_lookup_from_report(report: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    lookup: dict[tuple[str, str], dict[str, object]] = {}
    if "end_to_end_verdict_evaluation" in report:
        for mode, payload in report["end_to_end_verdict_evaluation"]["modes"].items():
            for case in payload["cases"]:
                lookup[(case["case_id"], mode)] = case
        return lookup
    for case in report.get("cases", []):
        for comparison in case.get("comparisons", []):
            lookup[(case["case_id"], comparison["mode"])] = comparison
    return lookup


def _oracle_before_after_summary(
    previous_report: dict[str, object] | None,
    current_report: dict[str, object],
) -> dict[str, object] | None:
    if previous_report is None:
        return None
    previous_lookup = _oracle_lookup_from_report(previous_report)
    current_lookup = _oracle_lookup_from_report(current_report)
    shared_case_ids = sorted(previous_lookup.keys() & current_lookup.keys())
    if not shared_case_ids:
        return None
    previous_cases = [previous_lookup[case_id] for case_id in shared_case_ids]
    current_cases = [current_lookup[case_id] for case_id in shared_case_ids]
    previous_summary = _precision_recall_f1(
        [case["expected_risk"] for case in previous_cases],
        [case["risk_label"] for case in previous_cases],
    )
    current_summary = _precision_recall_f1(
        [case["expected_risk"] for case in current_cases],
        [case["risk_label"] for case in current_cases],
    )
    previous_medium = _shared_case_outcomes(previous_cases, "verdict_matches_expectation", expected_label="medium prior-art risk")
    current_medium = _shared_case_outcomes(current_cases, "verdict_matches_expectation", expected_label="medium prior-art risk")
    previous_borderline = _shared_case_outcomes(previous_cases, "verdict_matches_expectation", case_type="borderline")
    current_borderline = _shared_case_outcomes(current_cases, "verdict_matches_expectation", case_type="borderline")
    return {
        "shared_case_ids": shared_case_ids,
        "accuracy_before": previous_summary["accuracy"],
        "accuracy_after": current_summary["accuracy"],
        "macro_f1_before": previous_summary["macro_f1"],
        "macro_f1_after": current_summary["macro_f1"],
        "mean_ordinal_error_before": previous_summary["mean_ordinal_error"],
        "mean_ordinal_error_after": current_summary["mean_ordinal_error"],
        "medium_match_rate_before": previous_medium["match_rate"],
        "medium_match_rate_after": current_medium["match_rate"],
        "borderline_match_rate_before": previous_borderline["match_rate"],
        "borderline_match_rate_after": current_borderline["match_rate"],
    }


def _before_after_summary(
    previous_report: dict[str, object] | None,
    current_report: dict[str, object],
) -> dict[str, object] | None:
    if previous_report is None:
        return None

    previous_lookup = _end_to_end_lookup_from_report(previous_report)
    current_lookup = _end_to_end_lookup_from_report(current_report)
    shared_case_ids = sorted(
        {case_id for case_id, _ in previous_lookup.keys()}
        & {case_id for case_id, _ in current_lookup.keys()}
    )
    current_case_ids = {case["case_id"] for case in current_report["cases"]}
    previous_case_ids = {case_id for case_id, _ in previous_lookup.keys()}
    summary: dict[str, object] = {
        "shared_case_ids": shared_case_ids,
        "new_case_ids": sorted(current_case_ids - previous_case_ids),
        "mode_deltas": {},
        "case_level_changes": [],
        "structure_changes": {
            "retrieval_layer_separated": "retrieval_evaluation" not in previous_report,
            "oracle_verdict_layer_added": "oracle_verdict_evaluation" not in previous_report,
            "end_to_end_layer_separated": "end_to_end_verdict_evaluation" not in previous_report,
        },
        "oracle_before_after": _oracle_before_after_summary(previous_report, current_report),
    }

    for mode in current_report["run_configuration"]["modes"]:
        previous_cases = [
            previous_lookup[(case_id, mode)]
            for case_id in shared_case_ids
            if (case_id, mode) in previous_lookup
        ]
        current_cases = [
            current_lookup[(case_id, mode)]
            for case_id in shared_case_ids
            if (case_id, mode) in current_lookup
        ]
        if not previous_cases or not current_cases:
            continue
        previous_verdict_matches = sum(1 for item in previous_cases if item["verdict_matches_expectation"])
        current_verdict_matches = sum(1 for item in current_cases if item["verdict_matches_expectation"])
        previous_low_predictions = sum(1 for item in previous_cases if item["risk_label"] == "low prior-art risk")
        current_low_predictions = sum(1 for item in current_cases if item["risk_label"] == "low prior-art risk")
        previous_high_predictions = sum(1 for item in previous_cases if item["risk_label"] == "high prior-art risk")
        current_high_predictions = sum(1 for item in current_cases if item["risk_label"] == "high prior-art risk")
        summary["mode_deltas"][mode] = {
            "shared_case_count": len(shared_case_ids),
            "verdict_match_rate_before": round(previous_verdict_matches / len(shared_case_ids), 4),
            "verdict_match_rate_after": round(current_verdict_matches / len(shared_case_ids), 4),
            "low_label_count_before": previous_low_predictions,
            "low_label_count_after": current_low_predictions,
            "high_label_count_before": previous_high_predictions,
            "high_label_count_after": current_high_predictions,
        }

    for case_id in shared_case_ids:
        for mode in current_report["run_configuration"]["modes"]:
            previous_case = previous_lookup.get((case_id, mode))
            current_case = current_lookup.get((case_id, mode))
            if previous_case is None or current_case is None:
                continue
            if previous_case["risk_label"] != current_case["risk_label"]:
                summary["case_level_changes"].append(
                    {
                        "case_id": case_id,
                        "mode": mode,
                        "risk_label_before": previous_case["risk_label"],
                        "risk_label_after": current_case["risk_label"],
                        "risk_score_before": previous_case["risk_score"],
                        "risk_score_after": current_case["risk_score"],
                    }
                )
    return summary


def _classify_oracle_failure(case: dict[str, object]) -> str:
    if case["verdict_matches_expectation"]:
        return "ok"
    if case["case_type"] == "near_duplicate":
        return "near_duplicate_miss"
    if (
        case["case_type"] == "borderline"
        and case["expected_risk"] == "medium prior-art risk"
        and case["risk_label"] == "low prior-art risk"
    ):
        return "borderline_underfire"
    if (
        case["risk_label"] == "high prior-art risk"
        and case.get("oracle_evidence_sufficiency") != "sufficient"
    ):
        return "insufficient_evidence_high_verdict"
    if case["debug"].get("lexical_only_count", 0) > 0 and case["risk_label"] != "low prior-art risk":
        return "lexical_overfire"
    return "oracle_wrong"


def _classify_end_to_end_failure(
    case: dict[str, object],
    oracle_case: dict[str, object],
) -> str:
    if case["verdict_matches_expectation"]:
        return "ok"
    if case["case_type"] == "near_duplicate" and case["expected_risk"] == "high prior-art risk":
        return "near_duplicate_miss"
    if case["debug"].get("lexical_only_count", 0) > 0 and case["risk_label"] != "low prior-art risk":
        return "lexical_overfire"
    if (
        case["case_type"] == "borderline"
        and case["expected_risk"] == "medium prior-art risk"
        and case["risk_label"] == "low prior-art risk"
    ):
        return "borderline_underfire"
    if (
        case["risk_label"] == "high prior-art risk"
        and case.get("oracle_evidence_sufficiency") != "sufficient"
    ):
        return "insufficient_evidence_high_verdict"
    if not case["retrieval_success"] and case["admissible_expected_evidence_ids"]:
        return "retrieval_miss"
    if not oracle_case["verdict_matches_expectation"]:
        return "oracle_wrong"
    return "oracle_wrong"


def _failure_breakdown(items: list[dict[str, object]], key: str) -> dict[str, int]:
    breakdown = {name: 0 for name in FAILURE_TYPES}
    for item in items:
        breakdown[str(item[key])] = breakdown.get(str(item[key]), 0) + 1
    return breakdown


def _error_observations(
    retrieval_cases: list[dict[str, object]],
    oracle_cases: list[dict[str, object]],
    end_to_end_cases: list[dict[str, object]],
) -> list[str]:
    observations: list[str] = []
    retrieval_misses = [case for case in retrieval_cases if case["failure_type"] == "retrieval_miss"]
    lexical_overfire = [case for case in end_to_end_cases if case["failure_type"] == "lexical_overfire"]
    oracle_errors = [case for case in oracle_cases if case["failure_type"] != "ok"]
    insufficient_high = [
        case for case in end_to_end_cases
        if case["failure_type"] == "insufficient_evidence_high_verdict"
    ]
    if retrieval_misses:
        observations.append(
            f"Retrieval misses remain on {len(retrieval_misses)} positive case-mode pairs after admissibility filtering."
        )
    if oracle_errors:
        observations.append(
            f"Oracle verdict mismatches remain on {len(oracle_errors)} curated cases, showing residual calibration limits beyond retrieval."
        )
    if lexical_overfire:
        observations.append(
            f"Lexical-overfire behaviour remains on {len(lexical_overfire)} end-to-end case-mode pairs."
        )
    if insufficient_high:
        observations.append(
            f"{len(insufficient_high)} case-mode pairs still produce high verdicts on only partial or insufficient admissible evidence."
        )
    return observations


def _retrieval_observations(report: dict[str, object], modes: list[str]) -> list[str]:
    observations: list[str] = []
    for mode in modes:
        summary = report["modes"][mode]["summary"]
        observations.append(
            f"{mode}: hit@3={summary['positive_hit_top3_count']}/{summary['positive_case_count']}, "
            f"negative clear={summary['negative_clear_count']}/{summary['negative_case_count']}, "
            f"retrieval success={summary['retrieval_success_rate']:.2f}."
        )
    return observations


def _end_to_end_observations(report: dict[str, object], modes: list[str]) -> list[str]:
    observations: list[str] = []
    for mode in modes:
        summary = report["modes"][mode]["summary"]
        observations.append(
            f"{mode}: accuracy={summary['accuracy']:.2f}, macro-F1={summary['macro_f1']:.2f}, "
            f"borderline match={summary['borderline_match_rate']:.2f}, "
            f"mean ordinal error={summary['mean_ordinal_error']:.2f}."
        )
    return observations


def _markdown_diagnostic_line(item: dict[str, object]) -> str:
    return (
        f"- {item['case_id']} [{item['mode']}] {item['case_type']}: expected={item['expected_risk']}, "
        f"oracle={item['oracle_verdict']} ({item['oracle_risk_score']:.2f}), "
        f"end-to-end={item['end_to_end_verdict']} ({item['end_to_end_risk_score']:.2f}), "
        f"failure={item['failure_type']}, top={item['top_evidence_ids']}, "
        f"oracle_top={item['top_oracle_evidence_ids']}, "
        f"oracle_state={item['oracle_evidence_sufficiency_state']}, end_state={item['end_to_end_evidence_sufficiency_state']}, "
        f"decision={item['triggered_decision_summary']}"
    )


def _markdown_summary(report: dict[str, object]) -> str:
    review_summary = report["dataset_summary"]["review_adjudication_summary"]
    oracle_summary = report["oracle_verdict_evaluation"]["summary"]
    temporal = report["dataset_summary"]["temporal_admissibility_summary"]
    lines = [
        "# Curated Experiment Notes",
        "",
        "## Dataset Summary",
        f"- curated document count: {report['corpus_summary']['document_count']}",
        f"- curated case count: {report['dataset_summary']['case_count']}",
        f"- oracle annotation coverage: {report['dataset_summary']['oracle_annotation_coverage']}",
        f"- protocol doc: {report['annotation_protocol']['path']}",
        "- case type distribution:",
    ]
    lines.extend(
        f"  - {case_type}: {count}"
        for case_type, count in report["dataset_summary"]["case_type_distribution"].items()
    )
    lines.extend([
        "",
        "## Review / Adjudication Summary",
        f"- labels changed on review: {review_summary['label_changes_on_review']}",
        f"- case types changed on review: {review_summary['case_type_changes_on_review']}",
        f"- oracle evidence sufficiency judgments changed on review: {review_summary['oracle_evidence_sufficiency_changes_on_review']}",
        "",
        "## Retrieval Evaluation",
    ])
    lines.extend(f"- {item}" for item in report["retrieval_evaluation"]["observations"])
    lines.extend([
        "",
        "## Oracle Verdict Evaluation",
        f"- accuracy={oracle_summary['accuracy']:.2f}, macro-F1={oracle_summary['macro_f1']:.2f}, mean ordinal error={oracle_summary['mean_ordinal_error']:.2f}",
        f"- medium-risk match rate={oracle_summary['medium_label_match_rate']:.2f}",
        f"- borderline-case match rate={oracle_summary['borderline_match_rate']:.2f}",
        f"- low↔medium confusion={oracle_summary['adjacent_confusion_summary']['low_to_medium'] + oracle_summary['adjacent_confusion_summary']['medium_to_low']}, "
        f"medium↔high confusion={oracle_summary['adjacent_confusion_summary']['medium_to_high'] + oracle_summary['adjacent_confusion_summary']['high_to_medium']}",
        f"- temporal admissibility: admissible={temporal['oracle_admissible_evidence_count']}, inadmissible={temporal['oracle_inadmissible_evidence_count']}",
        "",
        "## End-to-End Evaluation",
    ])
    lines.extend(f"- {item}" for item in report["end_to_end_verdict_evaluation"]["observations"])
    lines.extend([
        "",
        "## Diagnostics",
        "- failure type breakdown:",
    ])
    lines.extend(
        f"  - {name}: {count}"
        for name, count in report["diagnostics"]["failure_type_breakdown"].items()
        if count
    )
    lines.append("- per-case diagnostics:")
    lines.extend(_markdown_diagnostic_line(item) for item in report["diagnostics"]["per_case_mode"])
    lines.extend([
        "",
        "## Calibration",
    ])
    lines.extend(f"- {item}" for item in report["calibration_block"]["applied_changes"])
    oracle_before_after = report["calibration_block"].get("oracle_before_after")
    if oracle_before_after:
        lines.append(
            f"- oracle accuracy {oracle_before_after['accuracy_before']:.2f} -> {oracle_before_after['accuracy_after']:.2f}; "
            f"macro-F1 {oracle_before_after['macro_f1_before']:.2f} -> {oracle_before_after['macro_f1_after']:.2f}; "
            f"mean ordinal error {oracle_before_after['mean_ordinal_error_before']:.2f} -> {oracle_before_after['mean_ordinal_error_after']:.2f}"
        )
        lines.append(
            f"- medium-risk match {oracle_before_after['medium_match_rate_before']:.2f} -> {oracle_before_after['medium_match_rate_after']:.2f}; "
            f"borderline match {oracle_before_after['borderline_match_rate_before']:.2f} -> {oracle_before_after['borderline_match_rate_after']:.2f}"
        )
    lines.extend(["", "## Error Observations"])
    lines.extend(f"- {item}" for item in report["error_observations"])
    lines.extend(["", "## Limitation Notes"])
    lines.extend(f"- {item}" for item in report["limitation_notes"])
    before_after = report.get("before_after_comparison")
    if before_after:
        lines.extend(["", "## Before vs After"])
        lines.append(
            f"- shared legacy cases: {len(before_after['shared_case_ids'])}; new curated controls: {len(before_after['new_case_ids'])}"
        )
        structure_changes = before_after.get("structure_changes", {})
        if any(structure_changes.values()):
            lines.append("- structural evaluation changes:")
            if structure_changes.get("retrieval_layer_separated"):
                lines.append("  - retrieval evaluation is now reported as its own layer.")
            if structure_changes.get("oracle_verdict_layer_added"):
                lines.append("  - oracle-evidence verdict evaluation was added in this pass.")
            if structure_changes.get("end_to_end_layer_separated"):
                lines.append("  - end-to-end verdict evaluation is now reported separately from retrieval.")
        for mode, delta in before_after["mode_deltas"].items():
            lines.append(
                f"- {mode}: verdict match {delta['verdict_match_rate_before']:.2f} -> {delta['verdict_match_rate_after']:.2f}; "
                f"low labels {delta['low_label_count_before']} -> {delta['low_label_count_after']}; "
                f"high labels {delta['high_label_count_before']} -> {delta['high_label_count_after']}."
            )
    return "\n".join(lines) + "\n"


def run_curated_experiment(
    config: AppConfig,
    output_path: Path | None = None,
    notes_path: Path | None = None,
    modes: list[str] | None = None,
) -> dict[str, object]:
    selected_modes = modes or config.evaluation.default_modes
    expectations = _load_expectations(config.paths.curated_eval_expectations_path)
    cases = _load_curated_cases(config.paths.curated_eval_dir)
    corpus_map = _load_curated_corpus(config.paths.curated_raw_corpus_path)
    previous_report = None
    if output_path is not None and output_path.exists():
        previous_report = json.loads(output_path.read_text(encoding="utf-8"))

    retrieval_case_results: list[dict[str, object]] = []
    end_to_end_case_results: list[dict[str, object]] = []
    oracle_case_results: list[dict[str, object]] = []
    per_case_mode_diagnostics: list[dict[str, object]] = []
    grouped_cases: list[dict[str, object]] = []
    oracle_reranker = (
        OverlapReranker(config.reranker)
        if config.reranker.strategy == "overlap"
        else NoOpReranker()
    )

    temporal_summary = {
        "oracle_admissible_evidence_count": 0,
        "oracle_inadmissible_evidence_count": 0,
        "retrieval_inadmissible_prefilter_count": 0,
        "case_modes_with_inadmissible_prefilter": 0,
    }

    for idea in cases:
        expected = expectations.get(idea.idea_id, {})
        case_type = _case_type(expected)
        expected_risk = _truth_label(expected)
        cutoff_year = int(expected.get("cutoff_year", 9999))
        oracle_sufficiency = str(expected.get("oracle_evidence_sufficiency", "unspecified"))
        expected_relevant_ids = list(expected.get("expected_relevant_paper_ids", []))
        oracle_evidence_ids = list(expected.get("oracle_evidence_ids", []))
        admissible_expected_ids, inadmissible_expected_ids, missing_expected_ids = _filter_admissible_ids(
            expected_relevant_ids,
            cutoff_year,
            corpus_map,
        )
        admissible_oracle_ids, inadmissible_oracle_ids, missing_oracle_ids = _filter_admissible_ids(
            oracle_evidence_ids,
            cutoff_year,
            corpus_map,
        )
        temporal_summary["oracle_admissible_evidence_count"] += len(admissible_oracle_ids)
        temporal_summary["oracle_inadmissible_evidence_count"] += len(inadmissible_oracle_ids)

        case_entry = {
            "case_id": idea.idea_id,
            "title": idea.title,
            "expected_risk": expected_risk,
            "case_type": case_type,
            "cutoff_year": cutoff_year,
            "expected_relevant_paper_ids": expected_relevant_ids,
            "admissible_expected_relevant_paper_ids": admissible_expected_ids,
            "inadmissible_expected_relevant_paper_ids": inadmissible_expected_ids,
            "oracle_evidence_ids": oracle_evidence_ids,
            "admissible_oracle_evidence_ids": admissible_oracle_ids,
            "inadmissible_oracle_evidence_ids": inadmissible_oracle_ids,
            "annotation_rationale": expected.get("annotation_rationale", ""),
            "control_note": expected.get("control_note", ""),
            "failure_mode": expected.get("failure_mode", ""),
            "initial_label": expected.get("initial_label", expected_risk),
            "review_label": expected.get("review_label", expected_risk),
            "adjudicated_label": expected_risk,
            "initial_case_type": expected.get("initial_case_type", case_type),
            "review_case_type": expected.get("review_case_type", case_type),
            "oracle_evidence_sufficiency": oracle_sufficiency,
            "comparisons": [],
        }

        oracle_candidates, oracle_missing_ids = _oracle_candidates(idea, admissible_oracle_ids, corpus_map)
        oracle_reranked = oracle_reranker.rerank(idea, oracle_candidates)
        oracle_risk_score, oracle_risk_label, oracle_evidence, oracle_debug = score_candidates(
            oracle_reranked,
            config.scoring,
        )
        oracle_explanation = build_explanation(oracle_risk_label, oracle_risk_score, oracle_evidence)
        oracle_debug["retrieval_strategy"] = "oracle"
        oracle_debug["reranker_strategy"] = config.reranker.strategy
        oracle_case = {
            "case_id": idea.idea_id,
            "case_type": case_type,
            "expected_risk": expected_risk,
            "cutoff_year": cutoff_year,
            "oracle_evidence_ids": oracle_evidence_ids,
            "admissible_oracle_evidence_ids": admissible_oracle_ids,
            "inadmissible_oracle_evidence_ids": inadmissible_oracle_ids,
            "missing_oracle_ids": sorted(set(missing_oracle_ids + oracle_missing_ids)),
            "oracle_evidence_sufficiency": oracle_sufficiency,
            "review_label": expected.get("review_label", expected_risk),
            "adjudicated_label": expected_risk,
            "risk_label": oracle_risk_label,
            "risk_score": oracle_risk_score,
            "verdict_matches_expectation": oracle_risk_label == expected_risk,
            "evidence_strengths": [
                item.overlap_signals["debug_signals"].get("evidence_strength", "unknown")
                for item in oracle_evidence
            ],
            "top_papers": [item.paper_id for item in oracle_evidence[:3]],
            "admissible_evidence_count": len(admissible_oracle_ids),
            "inadmissible_evidence_count": len(inadmissible_oracle_ids),
            "debug": oracle_debug,
            "explanation": oracle_explanation,
        }
        oracle_case["failure_type"] = _classify_oracle_failure(oracle_case)
        oracle_case_results.append(oracle_case)

        for mode in selected_modes:
            corpus_config = with_corpus_paths(config, "curated")
            pipeline = PriorArtAssessmentPipeline(corpus_config, retrieval_strategy=mode)
            retrieved = pipeline.retriever.retrieve(idea)
            reranked = pipeline.reranker.rerank(idea, retrieved)
            admissible_reranked, inadmissible_retrieved_ids = _filter_admissible_candidates(reranked, cutoff_year)
            temporal_summary["retrieval_inadmissible_prefilter_count"] += len(inadmissible_retrieved_ids)
            if inadmissible_retrieved_ids:
                temporal_summary["case_modes_with_inadmissible_prefilter"] += 1

            end_risk_score, end_risk_label, end_evidence, end_debug = score_candidates(
                admissible_reranked,
                config.scoring,
            )
            end_explanation = build_explanation(end_risk_label, end_risk_score, end_evidence)
            end_debug["retrieval_strategy"] = mode
            end_debug["reranker_strategy"] = config.reranker.strategy
            top_evidence_ids = [item.paper_id for item in end_evidence[:3]]
            retrieval_success = (
                any(paper_id in top_evidence_ids for paper_id in admissible_expected_ids)
                if admissible_expected_ids
                else not top_evidence_ids
            )
            retrieval_entry = {
                "case_id": idea.idea_id,
                "case_type": case_type,
                "mode": mode,
                "cutoff_year": cutoff_year,
                "expected_relevant_paper_ids": expected_relevant_ids,
                "admissible_expected_evidence_ids": admissible_expected_ids,
                "inadmissible_expected_evidence_ids": inadmissible_expected_ids,
                "top_evidence_ids": top_evidence_ids,
                "inadmissible_top_candidate_ids": inadmissible_retrieved_ids[:3],
                "retrieval_hit_top3": any(paper_id in top_evidence_ids for paper_id in admissible_expected_ids) if admissible_expected_ids else False,
                "retrieval_success": retrieval_success,
                "top_paper_count": len(top_evidence_ids),
                "inadmissible_prefilter_count": len(inadmissible_retrieved_ids),
            }
            end_to_end_entry = {
                "case_id": idea.idea_id,
                "case_type": case_type,
                "mode": mode,
                "expected_risk": expected_risk,
                "cutoff_year": cutoff_year,
                "review_label": expected.get("review_label", expected_risk),
                "adjudicated_label": expected_risk,
                "oracle_evidence_sufficiency": oracle_sufficiency,
                "top_papers": top_evidence_ids,
                "admissible_expected_evidence_ids": admissible_expected_ids,
                "inadmissible_expected_evidence_ids": inadmissible_expected_ids,
                "inadmissible_top_candidate_ids": inadmissible_retrieved_ids[:3],
                "retrieval_hit_top3": retrieval_entry["retrieval_hit_top3"],
                "retrieval_success": retrieval_success,
                "risk_label": end_risk_label,
                "risk_score": end_risk_score,
                "verdict_matches_expectation": end_risk_label == expected_risk,
                "debug": end_debug,
                "explanation": end_explanation,
            }
            end_to_end_entry["failure_type"] = _classify_end_to_end_failure(end_to_end_entry, oracle_case)
            retrieval_entry["failure_type"] = (
                "ok"
                if retrieval_success
                else "near_duplicate_miss"
                if case_type == "near_duplicate"
                else "retrieval_miss"
            )
            retrieval_case_results.append(retrieval_entry)
            end_to_end_case_results.append(end_to_end_entry)
            diagnostic_record = {
                "case_id": idea.idea_id,
                "case_type": case_type,
                "mode": mode,
                "cutoff_year": cutoff_year,
                "expected_risk": expected_risk,
                "oracle_verdict": oracle_risk_label,
                "end_to_end_verdict": end_risk_label,
                "oracle_risk_score": oracle_risk_score,
                "end_to_end_risk_score": end_risk_score,
                "oracle_evidence_sufficiency_state": oracle_debug.get("evidence_sufficiency", "unknown"),
                "end_to_end_evidence_sufficiency_state": end_debug.get("evidence_sufficiency", "unknown"),
                "top_evidence_ids": top_evidence_ids,
                "top_oracle_evidence_ids": oracle_case["top_papers"],
                "admissible_expected_evidence_ids": admissible_expected_ids,
                "inadmissible_expected_evidence_ids": inadmissible_expected_ids,
                "admissible_oracle_evidence_ids": admissible_oracle_ids,
                "inadmissible_oracle_evidence_ids": inadmissible_oracle_ids,
                "inadmissible_top_candidate_ids": inadmissible_retrieved_ids[:3],
                "oracle_evidence_sufficiency": oracle_sufficiency,
                "oracle_failure_type": oracle_case["failure_type"],
                "failure_type": end_to_end_entry["failure_type"],
                "feature_values": {
                    "max_similarity": end_debug.get("max_similarity", 0.0),
                    "avg_top_similarity": end_debug.get("avg_top_similarity", 0.0),
                    "count_above_threshold": end_debug.get("count_above_threshold", 0),
                    "facet_coverage": end_debug.get("facet_coverage", 0.0),
                    "strong_support_count": end_debug.get("strong_support_count", 0),
                    "shallow_support_count": end_debug.get("shallow_support_count", 0),
                    "lexical_only_count": end_debug.get("lexical_only_count", 0),
                    "weak_support_count": end_debug.get("weak_support_count", 0),
                },
                "oracle_feature_values": {
                    "max_similarity": oracle_debug.get("max_similarity", 0.0),
                    "avg_top_similarity": oracle_debug.get("avg_top_similarity", 0.0),
                    "count_above_threshold": oracle_debug.get("count_above_threshold", 0),
                    "facet_coverage": oracle_debug.get("facet_coverage", 0.0),
                    "strong_support_count": oracle_debug.get("strong_support_count", 0),
                    "shallow_support_count": oracle_debug.get("shallow_support_count", 0),
                    "lexical_only_count": oracle_debug.get("lexical_only_count", 0),
                    "weak_support_count": oracle_debug.get("weak_support_count", 0),
                },
                "triggered_decision_summary": {
                    "oracle": oracle_debug.get("decision_basis", "unknown"),
                    "end_to_end": end_debug.get("decision_basis", "unknown"),
                    "oracle_scope_narrowing_required": bool(oracle_debug.get("scope_narrowing_required")),
                    "end_to_end_scope_narrowing_required": bool(end_debug.get("scope_narrowing_required")),
                    "oracle_high_blocked_by_insufficiency": bool(oracle_debug.get("high_blocked_by_insufficiency")),
                    "end_to_end_high_blocked_by_insufficiency": bool(end_debug.get("high_blocked_by_insufficiency")),
                    "limited_evidence_high_guard_applied": bool(
                        oracle_debug.get("limited_evidence_high_guard_applied")
                        or end_debug.get("limited_evidence_high_guard_applied")
                    ),
                },
            }
            per_case_mode_diagnostics.append(diagnostic_record)
            case_entry["comparisons"].append(
                {
                    "mode": mode,
                    "risk_label": end_risk_label,
                    "risk_score": end_risk_score,
                    "top_papers": top_evidence_ids,
                    "retrieval_hit_top3": retrieval_entry["retrieval_hit_top3"],
                    "verdict_matches_expectation": end_to_end_entry["verdict_matches_expectation"],
                    "failure_type": end_to_end_entry["failure_type"],
                    "debug": end_debug,
                }
            )

        grouped_cases.append(case_entry)

    retrieval_modes: dict[str, dict[str, object]] = {}
    for mode in selected_modes:
        mode_cases = [item for item in retrieval_case_results if item["mode"] == mode]
        positive_cases = [item for item in mode_cases if item["admissible_expected_evidence_ids"]]
        negative_cases = [item for item in mode_cases if not item["admissible_expected_evidence_ids"]]
        hit_count = sum(1 for item in positive_cases if item["retrieval_hit_top3"])
        negative_clear_count = sum(1 for item in negative_cases if not item["top_evidence_ids"])
        retrieval_success_count = sum(1 for item in mode_cases if item["retrieval_success"])
        retrieval_modes[mode] = {
            "summary": {
                "case_count": len(mode_cases),
                "positive_case_count": len(positive_cases),
                "positive_hit_top3_count": hit_count,
                "positive_hit_top3_rate": round(hit_count / len(positive_cases), 4) if positive_cases else 0.0,
                "negative_case_count": len(negative_cases),
                "negative_clear_count": negative_clear_count,
                "negative_clear_rate": round(negative_clear_count / len(negative_cases), 4) if negative_cases else 0.0,
                "retrieval_success_count": retrieval_success_count,
                "retrieval_success_rate": round(retrieval_success_count / len(mode_cases), 4) if mode_cases else 0.0,
                "inadmissible_prefilter_count": sum(item["inadmissible_prefilter_count"] for item in mode_cases),
                "no_evidence_cases": [item["case_id"] for item in mode_cases if not item["top_evidence_ids"]],
            },
            "case_type_breakdown": _case_type_breakdown(mode_cases, "retrieval_success"),
            "cases": mode_cases,
        }

    oracle_truth = [str(item["expected_risk"]) for item in oracle_case_results]
    oracle_predicted = [str(item["risk_label"]) for item in oracle_case_results]
    oracle_summary = _precision_recall_f1(oracle_truth, oracle_predicted)
    oracle_summary["case_type_breakdown"] = _case_type_breakdown(
        oracle_case_results,
        "verdict_matches_expectation",
    )
    oracle_summary["medium_label_match_rate"] = _shared_case_outcomes(
        oracle_case_results,
        "verdict_matches_expectation",
        expected_label="medium prior-art risk",
    )["match_rate"]
    oracle_summary["borderline_match_rate"] = _shared_case_outcomes(
        oracle_case_results,
        "verdict_matches_expectation",
        case_type="borderline",
    )["match_rate"]

    end_to_end_modes: dict[str, dict[str, object]] = {}
    for mode in selected_modes:
        mode_cases = [item for item in end_to_end_case_results if item["mode"] == mode]
        truth = [str(item["expected_risk"]) for item in mode_cases]
        predicted = [str(item["risk_label"]) for item in mode_cases]
        summary = _precision_recall_f1(truth, predicted)
        summary["average_risk_score"] = round(mean(item["risk_score"] for item in mode_cases), 4) if mode_cases else 0.0
        summary["mismatch_cases"] = [item["case_id"] for item in mode_cases if not item["verdict_matches_expectation"]]
        summary["case_type_breakdown"] = _case_type_breakdown(mode_cases, "verdict_matches_expectation")
        summary["medium_label_match_rate"] = _shared_case_outcomes(
            mode_cases,
            "verdict_matches_expectation",
            expected_label="medium prior-art risk",
        )["match_rate"]
        summary["borderline_match_rate"] = _shared_case_outcomes(
            mode_cases,
            "verdict_matches_expectation",
            case_type="borderline",
        )["match_rate"]
        end_to_end_modes[mode] = {
            "summary": summary,
            "cases": mode_cases,
        }

    report = {
        "corpus_summary": _corpus_summary(config),
        "annotation_protocol": {
            "path": str(config.paths.evaluation_annotation_protocol_path),
            "relative_to_fixed_corpus_snapshot": True,
            "relative_to_available_evidence": True,
            "absolute_novelty_detection": False,
        },
        "run_configuration": {
            "corpus": "curated",
            "modes": selected_modes,
            "top_k": config.retrieval.top_k,
            "reranker_strategy": config.reranker.strategy,
            "temporal_admissibility": "year cutoff applied to oracle evidence and evaluation scoring",
        },
        "dataset_summary": {
            "case_count": len(grouped_cases),
            "case_type_distribution": _case_type_distribution(expectations),
            "expected_label_distribution": _label_distribution(
                [_truth_label(item) for item in expectations.values()]
            ),
            "oracle_annotation_coverage": f"{sum(1 for item in expectations.values() if 'oracle_evidence_ids' in item)}/{len(expectations)}",
            "review_adjudication_summary": _review_adjudication_summary(expectations),
            "temporal_admissibility_summary": temporal_summary,
            "case_catalog": [
                {
                    "case_id": case["case_id"],
                    "case_type": case["case_type"],
                    "expected_risk": case["expected_risk"],
                    "cutoff_year": case["cutoff_year"],
                    "oracle_evidence_ids": case["oracle_evidence_ids"],
                    "annotation_rationale": case["annotation_rationale"],
                }
                for case in grouped_cases
            ],
        },
        "cases": grouped_cases,
        "retrieval_evaluation": {
            "modes": retrieval_modes,
            "observations": _retrieval_observations({"modes": retrieval_modes}, selected_modes),
        },
        "oracle_verdict_evaluation": {
            "summary": oracle_summary,
            "cases": oracle_case_results,
            "observations": [
                f"oracle: accuracy={oracle_summary['accuracy']:.2f}, macro-F1={oracle_summary['macro_f1']:.2f}, "
                f"medium-risk match={oracle_summary['medium_label_match_rate']:.2f}, "
                f"borderline match={oracle_summary['borderline_match_rate']:.2f}, "
                f"mean ordinal error={oracle_summary['mean_ordinal_error']:.2f}"
            ],
        },
        "end_to_end_verdict_evaluation": {
            "modes": end_to_end_modes,
            "observations": _end_to_end_observations({"modes": end_to_end_modes}, selected_modes),
        },
        "diagnostics": {
            "per_case_mode": per_case_mode_diagnostics,
            "failure_type_breakdown": _failure_breakdown(end_to_end_case_results, "failure_type"),
            "oracle_failure_type_breakdown": _failure_breakdown(oracle_case_results, "failure_type"),
        },
        "ablation_block": {
            "modes": {
                mode: {
                    "retrieval_hit_top3_rate": retrieval_modes[mode]["summary"]["positive_hit_top3_rate"],
                    "retrieval_success_rate": retrieval_modes[mode]["summary"]["retrieval_success_rate"],
                    "end_to_end_accuracy": end_to_end_modes[mode]["summary"]["accuracy"],
                    "end_to_end_macro_f1": end_to_end_modes[mode]["summary"]["macro_f1"],
                }
                for mode in selected_modes
            }
        },
        "calibration_block": {
            "applied_changes": [
                "Expanded curated evaluation to 10 curated documents and 12 curated cases with explicit review/adjudication metadata.",
                "Applied year-based temporal admissibility filtering before oracle and end-to-end verdict scoring inside the evaluation runner.",
                "Introduced a compact evidence-state rubric: self_sufficient, combination_sufficient, partial, and adjacent_only now shape verdict assignment before final label mapping.",
                "High verdicts are now allowed only for self_sufficient or combination_sufficient evidence states; raw high scores alone no longer escalate borderline or adjacent cases.",
                "Single-source adjacent support and narrower-scope support now surface through adjacent_only / partial states, with explicit insufficiency blocking in diagnostics.",
            ],
            "oracle_before_after": _oracle_before_after_summary(previous_report, {"oracle_verdict_evaluation": {"cases": oracle_case_results}}),
        },
        "error_observations": _error_observations(
            retrieval_case_results,
            oracle_case_results,
            end_to_end_case_results,
        ),
        "limitation_notes": [
            "The curated corpus is real-article-shaped but still compact and intentionally domain-focused.",
            "Expected risk labels remain protocol annotations assigned relative to the frozen curated corpus snapshot.",
            "Dense and hybrid retrieval still overfire on some semantically adjacent cases in a small corpus.",
            "Temporal admissibility is evaluation-only and does not yet constrain the normal runtime retrieval path itself.",
        ],
    }
    report["before_after_comparison"] = _before_after_summary(previous_report, report)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if notes_path is not None:
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        notes_path.write_text(_markdown_summary(report), encoding="utf-8")
    return report
