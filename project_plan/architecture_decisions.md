# Architecture Decisions

## Offline-First

The project starts offline-first because:

- reproducibility matters for a thesis
- local artifacts are easier to audit and describe
- the MVP should not depend on external APIs or unstable remote services
- small local corpora support fast iteration

## Modular Pipeline

The system is split into ingest, retrieval, rerank, scoring, explanation, and pipeline layers because:

- each stage can be evaluated separately
- later upgrades should not require a full rewrite
- the architecture becomes easier to describe in thesis methodology sections

## Rule-Based Verdict First

The first verdict implementation is rule-based because:

- it is deterministic
- it is explainable
- thresholds can be inspected and tuned
- it provides a stable baseline for future experiments

## Why Not LLM Judge First

LLM-only judging is not the first core path because:

- it is less reproducible
- it may hide decision logic
- it complicates thesis evaluation early
- it introduces extra dependencies without a strong baseline

## Why Sparse Baseline First

Sparse retrieval is first because:

- it is simple to implement locally
- it is easy to reason about
- it provides a meaningful comparison point for later dense or hybrid methods

## Planned Later

`Iteration 02+` is planned to add:

- dense retriever implementation or stub refinement
- hybrid fusion
- reranker abstraction with concrete implementations
- richer evidence structures
- evaluation harness and comparisons
