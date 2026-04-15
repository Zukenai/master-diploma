# Iteration 04 Results

## Summary

Iteration 04 implemented the first thesis-grade core experimental setup on top of the existing baseline architecture.

Implemented in this iteration:

- curated scholarly corpus acquisition from OpenAlex
- frozen local corpus snapshot and normalized corpus
- explicit provenance manifest and provenance record
- curated corpus indexing path
- curated experiment protocol with comparison across sparse, dense, and hybrid modes
- experiment outputs that separate retrieval observations from verdict observations

## Verification

Verified paths in Iteration 04:

- `sakana acquire-curated-corpus`
- `sakana index-curated-corpus`
- `sakana run-curated-experiment`
- `pytest`

Observed result:

- curated corpus acquisition succeeded with 7 real scholarly records
- curated corpus indexing succeeded
- curated experiment report and notes were generated locally
- test suite passed with `13 passed`

## Experimental Findings

The curated setup shows a more meaningful pattern than the toy-only setup:

- sparse retrieval is conservative and clears low-risk out-of-domain cases
- dense and hybrid retrieve relevant target-domain records reliably
- dense and hybrid still overfire on some low-risk cases because the curated corpus is small and tightly domain-focused
- retrieval quality and verdict quality can now be discussed separately in the repository artifacts

## Produced Artifacts

Key artifacts produced in this iteration:

- `data/raw/curated_scholarly_corpus.json`
- `data/raw/curated_openalex_snapshot.json`
- `data/provenance/curated_corpus_manifest.json`
- `data/provenance/curated_corpus_provenance.json`
- `data/processed/curated_normalized_corpus.json`
- `data/indexes/curated_sparse_index.json`
- `data/processed/curated_experiment_report.json`
- `data/processed/curated_experiment_notes.md`

## Remaining Limitations After Iteration 04

- the curated corpus is still intentionally small
- expected risk labels in the evaluation protocol remain controlled protocol annotations, not absolute novelty truth
- dense and hybrid modes still need calibration or stronger evidence logic on low-risk negative cases
- final thesis-oriented packaging, chapter formatting, and polished reproducibility presentation still remain for a later phase

## Final Constrained Pass

The final constrained pass inside Iteration 04 is limited to:

- adding a few curated controls
- minimally calibrating verdict behavior on the curated setup
- producing an explicit before-vs-after comparison

This pass is the intended stop point for core development.

After it, no more core logic changes should be needed unless a critical bug is found. The remaining work should be thesis-oriented packaging and presentation.

### What Changed

- added three curated controls focused on low-risk reviewer-operations language, borderline related-work screening, and patent-workflow lexical stress
- isolated curated experiment cases from the sample manual-eval directory
- minimally recalibrated the verdict logic by reducing similarity dominance and adding light penalties for shallow or lexical-only support
- added explicit before-vs-after reporting to the curated experiment outputs

### Verification

- `pytest` passed with `15 passed`
- `sakana run-curated-experiment` regenerated the curated experiment report and notes

### Before vs After Summary

On the shared legacy curated cases:

- dense verdict-match rate improved from `0.40` to `0.80`
- hybrid verdict-match rate improved from `0.40` to `1.00`
- sparse verdict-match rate stayed at `0.40`, but it no longer collapses all shared positives to uniformly low confidence

Case-level improvements on the legacy curated cases:

- `MANUAL-003` moved from false-positive high risk to low risk for `dense` and `hybrid`
- `MANUAL-004` moved from false-positive high risk to low risk for `dense` and `hybrid`
- `MANUAL-002` moved from false-positive high risk to medium risk for `hybrid`
- `MANUAL-001` moved from low risk to medium risk for `sparse`

### Remaining Limitations

- the curated corpus remains intentionally small and domain-focused
- `sparse` remains conservative on stronger positive cases
- `CURATED-008` still shows residual medium-risk inflation for `dense` and `hybrid`, which is acceptable as a documented limitation but not a reason for another core iteration

### Stop Decision

Core development should now stop.

Remaining work after this pass is thesis-oriented packaging, presentation, reproducibility framing, and chapter-friendly result organization.
