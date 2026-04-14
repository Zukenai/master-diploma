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

## Intentional Boundaries

- No dense retrieval in code yet
- No hybrid fusion in code yet
- No external APIs
- No PDF parsing
- No LLM judge

## Evolution Path

The package layout is already separated for later upgrades:

- `app/retrieval/base.py` for retriever interfaces
- `app/rerank/base.py` for reranker interfaces
- `app/scoring/` for transparent verdict logic
- `app/pipeline/` for orchestration

This allows `Iteration 02+` to add dense retrieval, hybrid fusion, and reranking without rewriting the MVP control flow.
