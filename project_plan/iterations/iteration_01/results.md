# Iteration 01 Results

## Summary

Iteration 01 produced the first runnable offline-first MVP baseline for prior-art risk assessment on a local toy corpus.

Implemented in this iteration:

- project structure and `project_plan/`
- Pydantic schemas
- local sample corpus
- ingestion and sparse index build
- sparse retrieval baseline
- rule-based scoring
- template-based explanation
- CLI commands
- docs and baseline tests

## Verification

Verified paths in Iteration 01:

- `sakana index-sample-corpus`
- `sakana assess-idea scripts/sample_idea.json`
- `sakana show-config`
- `pytest`

Observed result:

- the baseline produced valid JSON with `risk_label`, `risk_score`, `evidence`, `explanation`, `debug`
- tests passed on the local `.venv`

## Manual Eval Interpretation

The initial manual evaluation showed:

- overlap-heavy case looked broadly reasonable
- moderate semantic overlap was underdetected
- far out-of-domain case was handled correctly by sparse retrieval
- lexical trap case exposed false-positive risk from lexical overlap
- explanation quality was too shallow for anything beyond baseline inspection

## What This Iteration Established

Iteration 01 established:

- a reproducible engineering baseline
- a clear repository structure
- a durable planning layer inside the repo
- a stable sparse baseline for later comparison

## Remaining Limitations After Iteration 01

- retrieval was purely lexical
- no dense or hybrid retrieval
- no reranker integration
- evidence model was too thin
- no repeatable comparison harness
- corpus and manual eval were toy/local only
