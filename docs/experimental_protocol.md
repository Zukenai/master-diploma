# Experimental Protocol

## Scope

This protocol supports the core experimental phase of the thesis.

It distinguishes between:

- retrieval quality
- judgement or verdict quality

## Corpus

Two corpus modes now exist:

- `sample`: toy smoke-test corpus
- `curated`: small real scholarly corpus acquired offline from public metadata

## Baselines

Configured retrieval baselines:

- `sparse`
- `dense`
- `hybrid`

## Evaluation Inputs

Current evaluation uses the controlled idea cases in `scripts/manual_eval/` together with curated expectations in:

- `data/eval/curated_experiment_expectations.json`

## Outputs

The curated experiment generates:

- corpus summary
- run configuration summary
- per-case comparison outputs
- retrieval observations
- verdict observations
- limitation notes

These outputs are early thesis-grade experiment artifacts, not final chapter formatting.
