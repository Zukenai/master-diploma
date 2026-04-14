# Sakana: Prior-Art Risk Assessment Baseline

This repository contains an offline-first MVP baseline for a master's thesis module focused on literature-grounded prior-art risk assessment for research ideas.

The current implementation is intentionally limited to `Iteration 01`:

- local sample corpus
- deterministic ingestion and sparse retrieval
- rule-based scoring and verdict
- template-based explanation
- CLI workflow
- baseline tests and project planning artifacts

## Thesis Context

The broader thesis topic is:

`Agent-based AI system for automating scientific activity processes`

The main practical contribution in this repository is a narrower module:

`literature-grounded prior-art risk assessment`

The module does not claim to detect absolute scientific novelty. It estimates overlap risk relative to a selected local corpus and retrieval strategy.

## Quick Start

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

2. Build the local sample index:

```bash
sakana index-sample-corpus
```

3. Run assessment on the demo idea:

```bash
sakana assess-idea scripts/sample_idea.json
```

Optional retrieval modes:

```bash
sakana assess-idea scripts/sample_idea.json --retrieval-mode sparse
sakana assess-idea scripts/sample_idea.json --retrieval-mode dense
sakana assess-idea scripts/sample_idea.json --retrieval-mode hybrid
```

4. Show current config:

```bash
sakana show-config
```

5. Run tests:

```bash
pytest
```

## Repository Layout

- `app/` application code
- `data/raw/` sample corpus
- `data/processed/` normalized corpus artifacts
- `data/indexes/` retrieval index artifacts
- `docs/` technical documentation
- `project_plan/` roadmap, iteration files, and durable context
- `scripts/` runnable example inputs
- `tests/` baseline verification

## CLI Output Shape

Assessment returns JSON with:

- `risk_label`
- `risk_score`
- `evidence`
- `explanation`
- `debug`

## Scope Boundary

This repository does not currently implement:

- dense retrieval
- hybrid retrieval
- reranking
- web UI
- remote scholarly APIs
- PDF parsing
- LLM-as-judge core logic

Those are planned but intentionally deferred to later iterations and documented in `project_plan/`.
