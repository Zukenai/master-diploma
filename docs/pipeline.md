# Pipeline

## Input

The pipeline accepts an idea JSON file with:

- `idea_id`
- `title`
- `abstract`
- `keywords`
- `claims`

## Indexing

The sample corpus is stored in `data/raw/sample_corpus.json`.

The indexing command:

```bash
sakana index-sample-corpus
```

creates:

- `data/processed/normalized_corpus.json`
- `data/indexes/sparse_index.json`

## Retrieval

The baseline retriever:

- tokenizes title, abstract, keywords, and claims
- computes a weighted TF-IDF query vector
- scores local documents by cosine similarity
- returns top-k candidates with overlap metadata

## Scoring

The risk score uses transparent features:

- max similarity
- average top similarity
- count of retrieved papers above threshold
- aggregate keyword overlap across top evidence

Thresholds and weights live in `app/config/settings.py`.

## Output

The assessment result contains:

- `risk_label`
- `risk_score`
- `evidence`
- `explanation`
- `debug`

The output is intentionally thesis-friendly: deterministic, inspectable, and easy to describe in methodology and experiment chapters.
