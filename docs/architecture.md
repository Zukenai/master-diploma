# Architecture

## Current Baseline

`Iteration 01` implements a small offline-first pipeline:

1. `IdeaInput` JSON is validated with Pydantic.
2. Local sample corpus is normalized and indexed into a simple sparse TF-IDF structure.
3. `SparseRetriever` builds a weighted query from title, abstract, keywords, and claims.
4. Retrieved candidates are passed through a no-op reranker placeholder.
5. Rule-based scoring computes a risk score and discrete label.
6. Template-based explanation produces an evidence-grounded summary.
7. CLI prints a structured JSON result.

`Iteration 02` extends retrieval with:

1. `SparseRetriever` as the baseline path
2. `DenseRetriever` using local latent semantic embeddings built from TF-IDF + SVD
3. `HybridRetriever` using reciprocal-rank fusion over sparse and dense results
4. `OverlapReranker` as a minimal reranker-ready layer

`Iteration 03` extends decision quality with:

1. claim-aware and facet-aware overlap signals
2. richer scoring debug for comparative analysis
3. a repeatable manual evaluation harness across retrieval modes

`Iteration 04` extends the repository into core experimental setup:

1. small curated scholarly corpus acquisition from public metadata
2. provenance tracking and frozen local corpus snapshot
3. local indexing and retrieval on the curated corpus
4. experiment protocol outputs separated into retrieval and verdict observations

## Intentional Boundaries

- No dense retrieval in code yet
- No hybrid fusion in code yet
- No external APIs
- No PDF parsing
- No LLM judge

## Evolution Path

The package layout is already separated for later upgrades:

- `app/retrieval/base.py` for retriever interfaces
- `app/retrieval/dense.py` for local dense retrieval
- `app/retrieval/hybrid.py` for reproducible fusion
- `app/rerank/base.py` for reranker interfaces
- `app/scoring/` for transparent verdict logic
- `app/pipeline/` for orchestration

This allows `Iteration 02+` to add dense retrieval, hybrid fusion, and reranking without rewriting the MVP control flow.
