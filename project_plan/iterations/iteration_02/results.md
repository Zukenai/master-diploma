# Iteration 02 Results

## Summary

Iteration 02 upgraded retrieval architecture while preserving the runnable Iteration 01 baseline path.

Implemented in this iteration:

- retriever abstraction
- local dense retrieval using TF-IDF plus latent semantic reduction
- hybrid retrieval using reciprocal-rank fusion
- reranker abstraction and baseline overlap reranker
- richer evidence model with retriever-aware scores
- CLI compatibility with optional retrieval mode selection

## Verification

Verified paths in Iteration 02:

- `sakana index-sample-corpus`
- `sakana assess-idea scripts/sample_idea.json --retrieval-mode sparse`
- `sakana assess-idea scripts/sample_idea.json --retrieval-mode dense`
- `sakana assess-idea scripts/sample_idea.json --retrieval-mode hybrid`
- `pytest`

Observed result:

- all three retrieval paths ran through the CLI
- the JSON contract remained compatible
- the test suite passed after the retrieval upgrade

## Manual Eval Interpretation

Compared with Iteration 01:

- overlap-heavy cases became easier to retrieve and score highly
- moderate overlap cases were surfaced more strongly
- dense and hybrid paths on the toy corpus became too aggressive on some cases
- far case and lexical trap case still showed inflated risk under dense or hybrid modes

## What This Iteration Established

Iteration 02 established:

- multi-path retrieval architecture
- retriever-aware evidence output
- a cleaner extension point for future reranking and evidence logic
- a stronger baseline for retrieval comparisons

## Remaining Limitations After Iteration 02

- decision quality still lagged behind retrieval richness
- scoring was still not claim-aware enough
- semantic drift on the toy corpus could inflate risk
- comparison of retrieval modes was still mostly manual
