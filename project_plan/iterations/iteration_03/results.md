# Iteration 03 Results

## Summary

Iteration 03 focused on improving decision quality and adding a repeatable comparison harness without changing the basic Iteration 02 retrieval architecture.

Implemented in this iteration:

- claim-aware overlap signals
- facet-aware overlap signals across title, keywords, and claims
- richer scoring debug fields
- evaluation harness for comparing sparse, dense, and hybrid modes
- manual-eval expectations file
- CLI command for repeatable manual-case comparison

## Verification

Verified paths in Iteration 03:

- `sakana index-sample-corpus`
- `sakana evaluate-manual-cases`
- `pytest`

Observed result:

- the test suite passed with `10 passed`
- the evaluation harness produced repeatable JSON comparison reports
- CLI compatibility from earlier iterations was preserved

## Comparative Findings

Iteration 03 made the system more inspectable:

- verdicts now expose claim-aware and facet-aware evidence signals
- comparison across `sparse`, `dense`, and `hybrid` is now repeatable instead of chat-only
- experiment notes can now be grounded in explicit debug outputs

Observed comparison pattern on the toy setup:

- strong overlap case remained high risk across modes
- moderate overlap case often drifted upward to high risk
- sparse mode kept the far case at low risk
- dense and hybrid still pushed the far case into medium risk
- lexical trap case remained too risky across modes on the toy corpus

## What This Iteration Established

Iteration 03 established:

- a stronger evidence/scoring layer
- a repeatable manual evaluation harness
- baseline comparison outputs suitable for early experiment notes

## Remaining Limitations After Iteration 03

- the toy corpus still dominates system behaviour
- dense and hybrid modes still overfire on some out-of-domain or lexically misleading cases
- the system is still not operating on a curated scholarly corpus
- current evaluation is still engineering-grade, not yet a serious scholarly experiment
