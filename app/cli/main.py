from __future__ import annotations

import json
from pathlib import Path

import typer

from app.config.settings import get_config, with_corpus_paths
from app.evaluation.curated_experiment import run_curated_experiment
from app.evaluation.manual_eval import run_manual_evaluation
from app.ingest import acquire_curated_corpus
from app.ingest.indexer import build_sparse_index
from app.pipeline.assess import PriorArtAssessmentPipeline
from app.schemas.idea import IdeaInput

app = typer.Typer(help="Offline-first prior-art risk assessment baseline.")


def _index_corpus(raw_path: Path, processed_path: Path, index_path: Path) -> dict[str, object]:
    return build_sparse_index(
        raw_path=raw_path,
        processed_path=processed_path,
        index_path=index_path,
    )


@app.command("index-sample-corpus")
def index_sample_corpus() -> None:
    """Build processed corpus artifacts and sparse index from local sample data."""
    config = get_config()
    payload = _index_corpus(
        raw_path=config.paths.raw_corpus_path,
        processed_path=config.paths.processed_corpus_path,
        index_path=config.paths.sparse_index_path,
    )
    typer.echo(
        json.dumps(
            {
                "status": "ok",
                "document_count": payload["document_count"],
                "processed_path": str(config.paths.processed_corpus_path),
                "index_path": str(config.paths.sparse_index_path),
            },
            indent=2,
        )
    )


@app.command("acquire-curated-corpus")
def acquire_curated_corpus_command() -> None:
    """Fetch and freeze the curated scholarly corpus from public metadata sources."""
    config = get_config()
    payload = acquire_curated_corpus(config)
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command("index-curated-corpus")
def index_curated_corpus() -> None:
    """Build processed artifacts and sparse index for the curated scholarly corpus."""
    config = get_config()
    payload = _index_corpus(
        raw_path=config.paths.curated_raw_corpus_path,
        processed_path=config.paths.curated_processed_corpus_path,
        index_path=config.paths.curated_sparse_index_path,
    )
    typer.echo(
        json.dumps(
            {
                "status": "ok",
                "document_count": payload["document_count"],
                "processed_path": str(config.paths.curated_processed_corpus_path),
                "index_path": str(config.paths.curated_sparse_index_path),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


@app.command("assess-idea")
def assess_idea(
    input_path: Path,
    retrieval_mode: str = typer.Option(
        "",
        "--retrieval-mode",
        help="Retrieval mode: sparse, dense, or hybrid. Defaults to config strategy.",
    ),
    corpus: str = typer.Option(
        "sample",
        "--corpus",
        help="Corpus to use: sample or curated.",
    ),
) -> None:
    """Assess a research idea from a JSON file and print JSON result."""
    config = with_corpus_paths(get_config(), corpus)
    if not config.paths.sparse_index_path.exists():
        raise typer.BadParameter(
            f"Index not found at {config.paths.sparse_index_path}. Run `sakana index-sample-corpus` first."
        )
    if not config.paths.processed_corpus_path.exists():
        raise typer.BadParameter(
            f"Processed corpus not found at {config.paths.processed_corpus_path}. Run `sakana index-sample-corpus` first."
        )
    idea = IdeaInput.model_validate_json(input_path.read_text(encoding="utf-8"))
    pipeline = PriorArtAssessmentPipeline(config, retrieval_strategy=retrieval_mode or None)
    result = pipeline.assess(idea)
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))


@app.command("show-config")
def show_config() -> None:
    """Print the current application config."""
    config = get_config()
    typer.echo(json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False))


@app.command("evaluate-manual-cases")
def evaluate_manual_cases(
    output_path: Path | None = typer.Option(
        None,
        "--output-path",
        help="Optional path to save the evaluation report JSON.",
    ),
    modes: str = typer.Option(
        "",
        "--modes",
        help="Comma-separated retrieval modes to evaluate. Defaults to config modes.",
    ),
) -> None:
    """Run repeatable comparisons across the manual evaluation cases."""
    config = get_config()
    selected_modes = [mode.strip() for mode in modes.split(",") if mode.strip()] or None
    report = run_manual_evaluation(
        config,
        output_path=output_path or config.paths.manual_eval_report_path,
        modes=selected_modes,
    )
    typer.echo(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))


@app.command("run-curated-experiment")
def run_curated_experiment_command(
    output_path: Path | None = typer.Option(
        None,
        "--output-path",
        help="Optional path to save the curated experiment report JSON.",
    ),
    notes_path: Path | None = typer.Option(
        None,
        "--notes-path",
        help="Optional path to save curated experiment notes in Markdown.",
    ),
    modes: str = typer.Option(
        "",
        "--modes",
        help="Comma-separated retrieval modes to evaluate. Defaults to config modes.",
    ),
) -> None:
    """Run the curated scholarly experiment protocol and save chapter-friendly artifacts."""
    config = get_config()
    selected_modes = [mode.strip() for mode in modes.split(",") if mode.strip()] or None
    report = run_curated_experiment(
        config,
        output_path=output_path or config.paths.curated_experiment_report_path,
        notes_path=notes_path or config.paths.curated_experiment_notes_path,
        modes=selected_modes,
    )
    typer.echo(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
