from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from app.config.settings import AppConfig, with_corpus_paths
from app.pipeline.assess import PriorArtAssessmentPipeline
from app.schemas.idea import IdeaInput


def _load_expectations(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["case_id"]: item for item in payload}


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


def _mode_summary(case_results: list[dict[str, object]], mode: str) -> dict[str, object]:
    mode_cases = [case for case in case_results if case["mode"] == mode]
    retrieval_positive_cases = [case for case in mode_cases if case["expected_relevant_paper_ids"]]
    retrieval_negative_cases = [case for case in mode_cases if not case["expected_relevant_paper_ids"]]
    positive_hits = sum(1 for case in retrieval_positive_cases if case["retrieval_hit_top3"])
    negative_clear = sum(1 for case in retrieval_negative_cases if not case["top_papers"])
    return {
        "case_count": len(mode_cases),
        "positive_case_count": len(retrieval_positive_cases),
        "positive_hit_top3_count": positive_hits,
        "positive_hit_top3_rate": round(positive_hits / len(retrieval_positive_cases), 4)
        if retrieval_positive_cases
        else 0.0,
        "negative_case_count": len(retrieval_negative_cases),
        "negative_clear_count": negative_clear,
        "negative_clear_rate": round(negative_clear / len(retrieval_negative_cases), 4)
        if retrieval_negative_cases
        else 0.0,
        "no_evidence_cases": [case["case_id"] for case in mode_cases if not case["top_papers"]],
    }


def _verdict_mode_summary(case_results: list[dict[str, object]], mode: str) -> dict[str, object]:
    mode_cases = [case for case in case_results if case["mode"] == mode]
    verdict_matches = sum(1 for case in mode_cases if case["verdict_matches_expectation"])
    avg_risk = mean(case["risk_score"] for case in mode_cases) if mode_cases else 0.0
    label_counts: dict[str, int] = {}
    for case in mode_cases:
        label = case["risk_label"]
        label_counts[label] = label_counts.get(label, 0) + 1
    return {
        "case_count": len(mode_cases),
        "verdict_match_count": verdict_matches,
        "verdict_match_rate": round(verdict_matches / len(mode_cases), 4) if mode_cases else 0.0,
        "average_risk_score": round(avg_risk, 4),
        "label_counts": label_counts,
        "mismatch_cases": [
            case["case_id"] for case in mode_cases if not case["verdict_matches_expectation"]
        ],
    }


def _retrieval_observations(case_results: list[dict[str, object]], modes: list[str]) -> list[str]:
    observations: list[str] = []
    for mode in modes:
        summary = _mode_summary(case_results, mode)
        observations.append(
            f"{mode}: positive hit@3={summary['positive_hit_top3_count']}/{summary['positive_case_count']}, "
            f"negative clear={summary['negative_clear_count']}/{summary['negative_case_count']}."
        )
    return observations


def _verdict_observations(case_results: list[dict[str, object]], modes: list[str]) -> list[str]:
    observations: list[str] = []
    for mode in modes:
        summary = _mode_summary(case_results, mode)
        verdict_summary = _verdict_mode_summary(case_results, mode)
        observations.append(
            f"{mode}: verdict-match rate={verdict_summary['verdict_match_rate']:.2f}, "
            f"average risk score={verdict_summary['average_risk_score']:.2f}."
        )
    return observations


def _limitation_notes(case_results: list[dict[str, object]]) -> list[str]:
    notes = [
        "The curated corpus is real but still small and intentionally domain-focused.",
        "Expected risk labels are protocol annotations, not ground-truth statements about absolute novelty.",
        "Dense and hybrid retrieval can still overfire on semantically adjacent cases in a small corpus.",
    ]
    if any(case["expected_risk"] == "low prior-art risk" and case["risk_label"] != "low prior-art risk" for case in case_results):
        notes.append("At least one low-risk case is still elevated by some retrieval modes, indicating residual false-positive pressure.")
    return notes


def _compare_case_lookup(report: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    lookup: dict[tuple[str, str], dict[str, object]] = {}
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

    previous_lookup = _compare_case_lookup(previous_report)
    current_lookup = _compare_case_lookup(current_report)
    shared_case_ids = sorted(
        {case_id for case_id, _ in previous_lookup.keys()}
        & {case_id for case_id, _ in current_lookup.keys()}
    )
    current_case_ids = {case["case_id"] for case in current_report.get("cases", [])}
    previous_case_ids = {case["case_id"] for case in previous_report.get("cases", [])}
    summary: dict[str, object] = {
        "shared_case_ids": shared_case_ids,
        "new_case_ids": sorted(current_case_ids - previous_case_ids),
        "mode_deltas": {},
        "case_level_changes": [],
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
        previous_low_predictions = sum(
            1 for item in previous_cases if item["risk_label"] == "low prior-art risk"
        )
        current_low_predictions = sum(
            1 for item in current_cases if item["risk_label"] == "low prior-art risk"
        )
        previous_high_predictions = sum(
            1 for item in previous_cases if item["risk_label"] == "high prior-art risk"
        )
        current_high_predictions = sum(
            1 for item in current_cases if item["risk_label"] == "high prior-art risk"
        )
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


def _markdown_summary(report: dict[str, object]) -> str:
    lines = [
        "# Curated Experiment Notes",
        "",
        "## Corpus Summary",
        f"- document count: {report['corpus_summary']['document_count']}",
        f"- year range: {report['corpus_summary']['year_min']} to {report['corpus_summary']['year_max']}",
        "",
        "## Retrieval Observations",
    ]
    lines.extend(f"- {item}" for item in report["retrieval_observations"])
    lines.extend(["", "## Verdict Observations"])
    lines.extend(f"- {item}" for item in report["verdict_observations"])
    lines.extend(["", "## Limitation Notes"])
    lines.extend(f"- {item}" for item in report["limitation_notes"])
    before_after = report.get("before_after_comparison")
    if before_after:
        lines.extend(["", "## Before vs After"])
        lines.append(
            f"- shared legacy cases: {len(before_after['shared_case_ids'])}; new curated controls: {len(before_after['new_case_ids'])}"
        )
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
    previous_report = None
    if output_path is not None and output_path.exists():
        previous_report = json.loads(output_path.read_text(encoding="utf-8"))
    case_results: list[dict[str, object]] = []
    grouped_cases: list[dict[str, object]] = []

    for case_path in sorted(config.paths.curated_eval_dir.glob("*.json")):
        idea = IdeaInput.model_validate_json(case_path.read_text(encoding="utf-8"))
        expected = expectations.get(idea.idea_id, {})
        comparisons: list[dict[str, object]] = []

        for mode in selected_modes:
            corpus_config = with_corpus_paths(config, "curated")
            pipeline = PriorArtAssessmentPipeline(corpus_config, retrieval_strategy=mode)
            result = pipeline.assess(idea)
            expected_papers = expected.get("expected_relevant_paper_ids", [])
            top_papers = [item.paper_id for item in result.evidence[:3]]
            retrieval_hit = any(paper_id in top_papers for paper_id in expected_papers) if expected_papers else not top_papers
            verdict_match = result.risk_label == expected.get("expected_risk")
            comparison = {
                "mode": mode,
                "risk_label": result.risk_label,
                "risk_score": result.risk_score,
                "top_papers": top_papers,
                "retrieval_hit_top3": retrieval_hit,
                "verdict_matches_expectation": verdict_match,
                "debug": result.debug,
            }
            comparisons.append(comparison)
            case_results.append(
                {
                    "case_id": idea.idea_id,
                    "mode": mode,
                    "expected_risk": expected.get("expected_risk", "unspecified"),
                    "expected_relevant_paper_ids": expected_papers,
                    **comparison,
                }
            )

        grouped_cases.append(
            {
                "case_id": idea.idea_id,
                "title": idea.title,
                "expected_risk": expected.get("expected_risk", "unspecified"),
                "expected_relevant_paper_ids": expected.get("expected_relevant_paper_ids", []),
                "control_type": expected.get("control_type", "legacy"),
                "control_note": expected.get("control_note", ""),
                "failure_mode": expected.get("failure_mode", ""),
                "comparisons": comparisons,
            }
        )

    report = {
        "corpus_summary": _corpus_summary(config),
        "run_configuration": {
            "corpus": "curated",
            "modes": selected_modes,
            "top_k": config.retrieval.top_k,
            "reranker_strategy": config.reranker.strategy,
        },
        "cases": grouped_cases,
        "retrieval_summary": {mode: _mode_summary(case_results, mode) for mode in selected_modes},
        "verdict_summary": {mode: _verdict_mode_summary(case_results, mode) for mode in selected_modes},
        "retrieval_observations": _retrieval_observations(case_results, selected_modes),
        "verdict_observations": _verdict_observations(case_results, selected_modes),
        "limitation_notes": _limitation_notes(case_results),
    }
    report["before_after_comparison"] = _before_after_summary(previous_report, report)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if notes_path is not None:
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        notes_path.write_text(_markdown_summary(report), encoding="utf-8")
    return report
