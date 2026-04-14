# Manual Evaluation Notes

This file is for fast human inspection before `Iteration 02`.

## Goal

Run several hand-written ideas through the current baseline to see:

- where the verdict feels reasonable
- where the baseline is too lexical
- where explanation is weak
- where the verdict feels unstable or accidental

## Included Cases

- `scripts/manual_eval/idea_01_high_overlap.json`
- `scripts/manual_eval/idea_02_moderate_overlap.json`
- `scripts/manual_eval/idea_03_far_case.json`
- `scripts/manual_eval/idea_04_lexical_trap.json`
- `scripts/manual_eval/idea_05_borderline_case.json`

## How To Run

Make sure the index already exists:

```bash
source .venv/bin/activate
sakana index-sample-corpus
```

Run individual cases:

```bash
sakana assess-idea scripts/manual_eval/idea_01_high_overlap.json
sakana assess-idea scripts/manual_eval/idea_02_moderate_overlap.json
sakana assess-idea scripts/manual_eval/idea_03_far_case.json
sakana assess-idea scripts/manual_eval/idea_04_lexical_trap.json
sakana assess-idea scripts/manual_eval/idea_05_borderline_case.json
```

## What To Look At

For each run, check:

- Is `risk_label` intuitively plausible?
- Do the top evidence papers actually match the idea semantics?
- Is the result driven by a few exact words rather than the real concept?
- Does the explanation say anything useful beyond restating score and titles?
- Does `debug` help explain the label?

## Quick Interpretation Template

Record notes in this form:

- case id
- expected rough risk
- actual label and score
- top paper ids
- what looked right
- what looked too lexical
- what to improve in Iteration 02

## Likely Iteration 02 Follow-Ups

Manual evaluation is expected to expose:

- sparse lexical bias
- weak semantic generalization
- explanation templates that are too shallow
- need for denser evidence modeling
- need for reranking or hybrid retrieval
