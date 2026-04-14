from __future__ import annotations

import json
from pathlib import Path

from app.config.settings import AppConfig
from app.pipeline.assess import PriorArtAssessmentPipeline
from app.schemas.assessment import ManualEvalCaseResult, ManualEvalReport, ModeComparisonResult
from app.schemas.idea import IdeaInput


def _load_expectations(path: Path) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["case_id"]: item for item in payload}


def run_manual_evaluation(
    config: AppConfig,
    output_path: Path | None = None,
    modes: list[str] | None = None,
) -> ManualEvalReport:
    selected_modes = modes or config.evaluation.default_modes
    expectations = _load_expectations(config.paths.manual_eval_expectations_path)
    cases: list[ManualEvalCaseResult] = []
    label_counts: dict[str, int] = {}

    for case_path in sorted(config.paths.manual_eval_dir.glob("*.json")):
        idea = IdeaInput.model_validate_json(case_path.read_text(encoding="utf-8"))
        expected = expectations.get(idea.idea_id, {})
        comparisons: list[ModeComparisonResult] = []

        for mode in selected_modes:
            pipeline = PriorArtAssessmentPipeline(config, retrieval_strategy=mode)
            result = pipeline.assess(idea)
            label_counts[result.risk_label] = label_counts.get(result.risk_label, 0) + 1
            comparisons.append(
                ModeComparisonResult(
                    mode=mode,
                    risk_label=result.risk_label,
                    risk_score=result.risk_score,
                    top_papers=[item.paper_id for item in result.evidence[:3]],
                    debug=result.debug,
                )
            )

        cases.append(
            ManualEvalCaseResult(
                case_id=idea.idea_id,
                title=idea.title,
                expected_risk=expected.get("expected_risk", "unspecified"),
                comparisons=comparisons,
            )
        )

    summary = {
        "modes": selected_modes,
        "case_count": len(cases),
        "label_counts": label_counts,
    }
    report = ManualEvalReport(cases=cases, summary=summary)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return report
