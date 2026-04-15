# Curated Scholarly Corpus

This repository now includes a small curated real scholarly corpus intended for the thesis experimental setup.

## Source

- public metadata source: OpenAlex
- acquisition mode: offline corpus acquisition step only
- runtime dependency: none

## Corpus Purpose

The corpus is not a general scholarly search collection.

It is a controlled experimental corpus selected to evaluate:

- prior-art screening behavior
- claim-aware overlap behavior
- scholarly retrieval behavior for idea-assessment workflows

## Selection Logic

The selected records were chosen to cover:

- patent prior-art search and claim matching
- semantic prior-art retrieval
- scholarly literature retrieval benchmarking
- novelty assessment for research ideas

The exact selected works and their OpenAlex IDs are stored in:

- `data/provenance/curated_corpus_manifest.json`
- `data/provenance/curated_corpus_provenance.json`

## Known Limitations

- the corpus is intentionally small
- it is not exhaustive
- it is suitable for controlled baseline experiments, not for claims of complete literature coverage
- all system verdicts must still be interpreted relative to this selected corpus and retrieval strategy
