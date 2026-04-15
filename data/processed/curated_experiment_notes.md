# Curated Experiment Notes

## Dataset Summary
- document count: 7
- case count: 8
- oracle annotation coverage: 8/8
- protocol doc: docs/evaluation_annotation_protocol.md
- case type distribution:
  - near_duplicate: 1
  - borderline: 2
  - clear_negative: 1
  - lexical_stress: 2
  - clear_positive: 1
  - adjacent_distinct: 1

## Retrieval Evaluation
- sparse: hit@3=4/4, negative clear=2/4.
- dense: hit@3=4/4, negative clear=0/4.
- hybrid: hit@3=4/4, negative clear=0/4.

## Oracle Verdict Evaluation
- accuracy=0.62, macro-F1=0.47

## End-to-End Verdict Evaluation
- sparse: accuracy=0.62, macro-F1=0.43.
- dense: accuracy=0.75, macro-F1=0.72.
- hybrid: accuracy=0.88, macro-F1=0.89.

## Error Observations
- Oracle verdict mismatches remain on 3 curated cases, indicating verdict calibration limits beyond retrieval.
- End-to-end mismatches remain on 6 case-mode pairs.

## Limitation Notes
- The curated corpus is real but still small and intentionally domain-focused.
- Expected risk labels are protocol annotations assigned relative to the frozen curated corpus snapshot.
- Dense and hybrid retrieval can still overfire on semantically adjacent cases in a small corpus.
- Temporal admissibility filtering was not implemented in this pass.

## Evaluation Hardening Notes
- temporal admissibility support: not implemented in this pass
- explanation audit block: not implemented in this pass

## Before vs After
- shared legacy cases: 8; new curated controls: 0
- structural evaluation changes:
  - retrieval evaluation is now reported as its own layer.
  - oracle-evidence verdict evaluation was added in this pass.
  - end-to-end verdict evaluation is now reported separately from retrieval.
- sparse: verdict match 0.62 -> 0.62; low labels 6 -> 6; high labels 0 -> 0.
- dense: verdict match 0.75 -> 0.75; low labels 3 -> 3; high labels 3 -> 3.
- hybrid: verdict match 0.88 -> 0.88; low labels 3 -> 3; high labels 2 -> 2.
