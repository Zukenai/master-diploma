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
    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(sum(f1_values) / len(LABELS), 4),
        "per_label": per_label,
        "confusion": confusion,
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
        case_type = str(item.get("case_type", "unspecified"))
        distribution[case_type] = distribution.get(case_type, 0) + 1
    return distribution


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


def _case_lookup_from_report(report: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
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


def _before_after_summary(
    previous_report: dict[str, object] | None,
    current_report: dict[str, object],
) -> dict[str, object] | None:
    if previous_report is None:
        return None

    previous_lookup = _case_lookup_from_report(previous_report)
    current_lookup = _case_lookup_from_report(current_report)
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


def _error_observations(
    retrieval_cases: list[dict[str, object]],
    oracle_cases: list[dict[str, object]],
    end_to_end_cases: list[dict[str, object]],
) -> list[str]:
    observations: list[str] = []
    retrieval_misses = [
        case for case in retrieval_cases
        if case["expected_relevant_paper_ids"] and not case["retrieval_hit_top3"]
    ]
    if retrieval_misses:
        observations.append(
            f"Retrieval misses remain on {len(retrieval_misses)} positive case-mode pairs."
        )
    oracle_errors = [case for case in oracle_cases if not case["verdict_matches_expectation"]]
    if oracle_errors:
        observations.append(
            f"Oracle verdict mismatches remain on {len(oracle_errors)} curated cases, indicating verdict calibration limits beyond retrieval."
        )
    e2e_errors = [case for case in end_to_end_cases if not case["verdict_matches_expectation"]]
    if e2e_errors:
        observations.append(
            f"End-to-end mismatches remain on {len(e2e_errors)} case-mode pairs."
        )
    return observations


def _retrieval_observations(report: dict[str, object], modes: list[str]) -> list[str]:
    observations: list[str] = []
    for mode in modes:
        summary = report["modes"][mode]["summary"]
        observations.append(
            f"{mode}: hit@3={summary['positive_hit_top3_count']}/{summary['positive_case_count']}, "
            f"negative clear={summary['negative_clear_count']}/{summary['negative_case_count']}."
        )
    return observations


def _end_to_end_observations(report: dict[str, object], modes: list[str]) -> list[str]:
    observations: list[str] = []
    for mode in modes:
        summary = report["modes"][mode]["summary"]
        observations.append(
            f"{mode}: accuracy={summary['accuracy']:.2f}, macro-F1={summary['macro_f1']:.2f}."
        )
    return observations


def _markdown_summary(report: dict[str, object]) -> str:
    lines = [
        "# Curated Experiment Notes",
        "",
        "## Dataset Summary",
        f"- document count: {report['corpus_summary']['document_count']}",
        f"- case count: {report['dataset_summary']['case_count']}",
        f"- oracle annotation coverage: {report['dataset_summary']['oracle_annotation_coverage']}",
        f"- protocol doc: {report['annotation_protocol']['path']}",
        "- case type distribution:",
    ]
    lines.extend(
        f"  - {case_type}: {count}"
        for case_type, count in report["dataset_summary"]["case_type_distribution"].items()
    )
    lines.extend(["", "## Retrieval Evaluation"])
    lines.extend(f"- {item}" for item in report["retrieval_evaluation"]["observations"])
    lines.extend(["", "## Oracle Verdict Evaluation"])
    lines.append(
        f"- accuracy={report['oracle_verdict_evaluation']['summary']['accuracy']:.2f}, "
        f"macro-F1={report['oracle_verdict_evaluation']['summary']['macro_f1']:.2f}"
    )
    lines.extend(["", "## End-to-End Verdict Evaluation"])
    lines.extend(f"- {item}" for item in report["end_to_end_verdict_evaluation"]["observations"])
    lines.extend(["", "## Error Observations"])
    lines.extend(f"- {item}" for item in report["error_observations"])
    lines.extend(["", "## Limitation Notes"])
    lines.extend(f"- {item}" for item in report["limitation_notes"])
    lines.extend(["", "## Evaluation Hardening Notes"])
    lines.append("- temporal admissibility support: not implemented in this pass")
    lines.append("- explanation audit block: not implemented in this pass")
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
        if before_after["case_level_changes"]:
            lines.append("- case-level label changes:")
            lines.extend(
                f"  - {item['case_id']} ({item['mode']}): {item['risk_label_before']} -> {item['risk_label_after']}"
                for item in before_after["case_level_changes"]
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
    grouped_cases: list[dict[str, object]] = []
    oracle_reranker = (
        OverlapReranker(config.reranker)
        if config.reranker.strategy == "overlap"
        else NoOpReranker()
    )

    for idea in cases:
        expected = expectations.get(idea.idea_id, {})
        case_type = str(expected.get("case_type", "unspecified"))
        expected_papers = list(expected.get("oracle_evidence_ids", expected.get("expected_relevant_paper_ids", [])))
        case_entry = {
            "case_id": idea.idea_id,
            "title": idea.title,
            "expected_risk": expected.get("expected_risk", "unspecified"),
            "expected_relevant_paper_ids": list(expected.get("expected_relevant_paper_ids", [])),
            "oracle_evidence_ids": expected_papers,
            "case_type": case_type,
            "annotation_rationale": expected.get("annotation_rationale", ""),
            "control_note": expected.get("control_note", ""),
            "failure_mode": expected.get("failure_mode", ""),
            "comparisons": [],
        }

        oracle_candidates, missing_ids = _oracle_candidates(idea, expected_papers, corpus_map)
        oracle_reranked = oracle_reranker.rerank(idea, oracle_candidates)
        oracle_risk_score, oracle_risk_label, oracle_evidence, oracle_debug = score_candidates(
            oracle_reranked,
            config.scoring,
        )
        oracle_explanation = build_explanation(oracle_risk_label, oracle_risk_score, oracle_evidence)
        oracle_debug["retrieval_strategy"] = "oracle"
        oracle_debug["reranker_strategy"] = config.reranker.strategy
        oracle_case_results.append(
            {
                "case_id": idea.idea_id,
                "case_type": case_type,
                "expected_risk": expected.get("expected_risk", "unspecified"),
                "oracle_evidence_ids": expected_papers,
                "missing_oracle_ids": missing_ids,
                "risk_label": oracle_risk_label,
                "risk_score": oracle_risk_score,
                "verdict_matches_expectation": oracle_risk_label == expected.get("expected_risk"),
                "evidence_strengths": [
                    item.overlap_signals["debug_signals"].get("evidence_strength", "unknown")
                    for item in oracle_evidence
                ],
                "top_papers": [item.paper_id for item in oracle_evidence[:3]],
                "debug": oracle_debug,
                "explanation": oracle_explanation,
            }
        )

        for mode in selected_modes:
            corpus_config = with_corpus_paths(config, "curated")
            pipeline = PriorArtAssessmentPipeline(corpus_config, retrieval_strategy=mode)
            result = pipeline.assess(idea)
            top_papers = [item.paper_id for item in result.evidence[:3]]
            expected_relevant_ids = list(expected.get("expected_relevant_paper_ids", []))
            retrieval_hit = (
                any(paper_id in top_papers for paper_id in expected_relevant_ids)
                if expected_relevant_ids
                else not top_papers
            )
            retrieval_entry = {
                "case_id": idea.idea_id,
                "case_type": case_type,
                "mode": mode,
                "expected_relevant_paper_ids": expected_relevant_ids,
                "top_papers": top_papers,
                "retrieval_hit_top3": retrieval_hit,
                "top_paper_count": len(top_papers),
            }
            end_to_end_entry = {
                "case_id": idea.idea_id,
                "case_type": case_type,
                "mode": mode,
                "expected_risk": expected.get("expected_risk", "unspecified"),
                "risk_label": result.risk_label,
                "risk_score": result.risk_score,
                "top_papers": top_papers,
                "retrieval_hit_top3": retrieval_hit,
                "verdict_matches_expectation": result.risk_label == expected.get("expected_risk"),
                "debug": result.debug,
            }
            retrieval_case_results.append(retrieval_entry)
            end_to_end_case_results.append(end_to_end_entry)
            case_entry["comparisons"].append(
                {
                    "mode": mode,
                    "risk_label": result.risk_label,
                    "risk_score": result.risk_score,
                    "top_papers": top_papers,
                    "retrieval_hit_top3": retrieval_hit,
                    "verdict_matches_expectation": result.risk_label == expected.get("expected_risk"),
                    "debug": result.debug,
                }
            )

        grouped_cases.append(case_entry)

    retrieval_modes: dict[str, dict[str, object]] = {}
    for mode in selected_modes:
        mode_cases = [item for item in retrieval_case_results if item["mode"] == mode]
        positive_cases = [item for item in mode_cases if item["expected_relevant_paper_ids"]]
        negative_cases = [item for item in mode_cases if not item["expected_relevant_paper_ids"]]
        hit_count = sum(1 for item in positive_cases if item["retrieval_hit_top3"])
        negative_clear_count = sum(1 for item in negative_cases if not item["top_papers"])
        retrieval_modes[mode] = {
            "summary": {
                "case_count": len(mode_cases),
                "positive_case_count": len(positive_cases),
                "positive_hit_top3_count": hit_count,
                "positive_hit_top3_rate": round(hit_count / len(positive_cases), 4) if positive_cases else 0.0,
                "negative_case_count": len(negative_cases),
                "negative_clear_count": negative_clear_count,
                "negative_clear_rate": round(negative_clear_count / len(negative_cases), 4) if negative_cases else 0.0,
                "no_evidence_cases": [item["case_id"] for item in mode_cases if not item["top_papers"]],
            },
            "case_type_breakdown": _case_type_breakdown(mode_cases, "retrieval_hit_top3"),
            "cases": mode_cases,
        }

    oracle_truth = [str(item["expected_risk"]) for item in oracle_case_results]
    oracle_predicted = [str(item["risk_label"]) for item in oracle_case_results]
    oracle_summary = _precision_recall_f1(oracle_truth, oracle_predicted)
    oracle_summary["case_type_breakdown"] = _case_type_breakdown(
        oracle_case_results,
        "verdict_matches_expectation",
    )

    end_to_end_modes: dict[str, dict[str, object]] = {}
    for mode in selected_modes:
        mode_cases = [item for item in end_to_end_case_results if item["mode"] == mode]
        truth = [str(item["expected_risk"]) for item in mode_cases]
        predicted = [str(item["risk_label"]) for item in mode_cases]
        summary = _precision_recall_f1(truth, predicted)
        summary["average_risk_score"] = round(mean(item["risk_score"] for item in mode_cases), 4) if mode_cases else 0.0
        summary["mismatch_cases"] = [item["case_id"] for item in mode_cases if not item["verdict_matches_expectation"]]
        summary["case_type_breakdown"] = _case_type_breakdown(mode_cases, "verdict_matches_expectation")
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
            "temporal_admissibility": "not_implemented",
        },
        "dataset_summary": {
            "case_count": len(grouped_cases),
            "case_type_distribution": _case_type_distribution(expectations),
            "expected_label_distribution": _label_distribution(
                [str(item.get("expected_risk", "unspecified")) for item in expectations.values()]
            ),
            "oracle_annotation_coverage": f"{sum(1 for item in expectations.values() if 'oracle_evidence_ids' in item)}/{len(expectations)}",
            "case_catalog": [
                {
                    "case_id": case["case_id"],
                    "case_type": case["case_type"],
                    "expected_risk": case["expected_risk"],
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
                f"predicted labels={oracle_summary['predicted_label_distribution']}"
            ],
        },
        "end_to_end_verdict_evaluation": {
            "modes": end_to_end_modes,
            "observations": _end_to_end_observations({"modes": end_to_end_modes}, selected_modes),
        },
        "ablation_block": {
            "modes": {
                mode: {
                    "retrieval_hit_top3_rate": retrieval_modes[mode]["summary"]["positive_hit_top3_rate"],
                    "end_to_end_accuracy": end_to_end_modes[mode]["summary"]["accuracy"],
                    "end_to_end_macro_f1": end_to_end_modes[mode]["summary"]["macro_f1"],
                }
                for mode in selected_modes
            }
        },
        "error_observations": _error_observations(
            retrieval_case_results,
            oracle_case_results,
            end_to_end_case_results,
        ),
        "limitation_notes": [
            "The curated corpus is real but still small and intentionally domain-focused.",
            "Expected risk labels are protocol annotations assigned relative to the frozen curated corpus snapshot.",
            "Dense and hybrid retrieval can still overfire on semantically adjacent cases in a small corpus.",
            "Temporal admissibility filtering was not implemented in this pass.",
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
