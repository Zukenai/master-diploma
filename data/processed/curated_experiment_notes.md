# Curated Experiment Notes

## Corpus Summary
- document count: 7
- year range: 2020 to 2026

## Retrieval Observations
- sparse: positive hit@3=4/4, negative clear=2/4.
- dense: positive hit@3=4/4, negative clear=0/4.
- hybrid: positive hit@3=4/4, negative clear=0/4.

## Verdict Observations
- sparse: verdict-match rate=0.62, average risk score=0.26.
- dense: verdict-match rate=0.75, average risk score=0.61.
- hybrid: verdict-match rate=0.88, average risk score=0.58.

## Limitation Notes
- The curated corpus is real but still small and intentionally domain-focused.
- Expected risk labels are protocol annotations, not ground-truth statements about absolute novelty.
- Dense and hybrid retrieval can still overfire on semantically adjacent cases in a small corpus.
- At least one low-risk case is still elevated by some retrieval modes, indicating residual false-positive pressure.

## Before vs After
- shared legacy cases: 5; new curated controls: 3
- sparse: verdict match 0.40 -> 0.40; low labels 5 -> 4; high labels 0 -> 0.
- dense: verdict match 0.40 -> 0.80; low labels 0 -> 2; high labels 5 -> 3.
- hybrid: verdict match 0.40 -> 1.00; low labels 0 -> 2; high labels 5 -> 2.
- case-level label changes:
  - MANUAL-001 (sparse): low prior-art risk -> medium prior-art risk
  - MANUAL-002 (hybrid): high prior-art risk -> medium prior-art risk
  - MANUAL-003 (dense): high prior-art risk -> low prior-art risk
  - MANUAL-003 (hybrid): high prior-art risk -> low prior-art risk
  - MANUAL-004 (dense): high prior-art risk -> low prior-art risk
  - MANUAL-004 (hybrid): high prior-art risk -> low prior-art risk
