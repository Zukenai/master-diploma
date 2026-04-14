from __future__ import annotations

import json
from pathlib import Path

import typer

from app.config.settings import get_config
from app.ingest.indexer import build_sparse_index
from app.pipeline.assess import PriorArtAssessmentPipeline
from app.schemas.idea import IdeaInput

app = typer.Typer(help="Offline-first prior-art risk assessment baseline.")


@app.command("index-sample-corpus")
def index_sample_corpus() -> None:
    """Build processed corpus artifacts and sparse index from local sample data."""
    config = get_config()
    payload = build_sparse_index(
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


@app.command("assess-idea")
def assess_idea(input_path: Path) -> None:
    """Assess a research idea from a JSON file and print JSON result."""
    config = get_config()
    if not config.paths.sparse_index_path.exists():
        raise typer.BadParameter(
            f"Index not found at {config.paths.sparse_index_path}. Run `sakana index-sample-corpus` first."
        )
    idea = IdeaInput.model_validate_json(input_path.read_text(encoding="utf-8"))
    pipeline = PriorArtAssessmentPipeline(config)
    result = pipeline.assess(idea)
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))


@app.command("show-config")
def show_config() -> None:
    """Print the current application config."""
    config = get_config()
    typer.echo(json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
