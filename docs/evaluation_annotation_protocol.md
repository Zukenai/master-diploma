# Evaluation Annotation Protocol

This guide defines the compact annotation protocol for curated evaluation cases in this repository.

## Label Definitions

- `low prior-art risk`: the curated corpus does not provide evidence of substantive overlap strong enough to treat the idea as already covered.
- `medium prior-art risk`: the curated corpus contains meaningful overlap evidence, but not enough to treat the idea as a clear near-duplicate or strong prior-art match.
- `high prior-art risk`: the curated corpus contains strong evidence that the idea substantially overlaps with prior work in task, contribution, or claim framing.

## Scope Constraints

- Labels are assigned relative to the frozen curated corpus snapshot in this repository.
- Labels are assigned relative to the available evidence in that snapshot.
- Labels do not claim absolute scientific novelty detection.

## Evidence Strength Categories

- `direct overlap`: overlap is visible in claim-level and title/task framing.
- `multi-facet overlap`: overlap appears across more than one facet, such as title, keyword, and claim signals.
- `partial overlap`: overlap is present but concentrated in one substantive facet only.
- `lexical-only similarity`: shared wording exists without enough substantive overlap signals.
- `adjacent-but-distinct similarity`: the idea is domain-adjacent but functionally distinct from the evidence.

## Curated Case Metadata

Each curated case must define:

- `case_id`
- `case_type`
- `expected_risk`
- `oracle_evidence_ids`
- `cutoff_year`
- `initial_label`
- `review_label`
- `adjudicated_label`
- `initial_case_type`
- `review_case_type`
- `initial_oracle_evidence_sufficiency`
- `review_oracle_evidence_sufficiency`
- `oracle_evidence_sufficiency`
- `annotation_rationale`

`expected_risk` is retained for readability, but experiment scoring uses `adjudicated_label` as the evaluation target when it is present.

## Oracle Evidence Sufficiency

- `sufficient`: admissible oracle evidence is strong enough to support the adjudicated label.
- `partial`: admissible oracle evidence supports related overlap, but the final label still depends on cautious interpretation.
- `insufficient`: admissible oracle evidence is absent or too weak to justify anything above low risk.

## Review / Adjudication Layer

- `initial_*` fields capture the first-pass annotation.
- `review_*` fields capture the compact second-pass review.
- final `case_type`, `adjudicated_label`, and `oracle_evidence_sufficiency` are the values used in evaluation.

## Deterministic Failure-Type Mapping

The experiment runner assigns compact failure types with deterministic rules:

- `ok`
- `retrieval_miss`
- `oracle_wrong`
- `lexical_overfire`
- `borderline_underfire`
- `near_duplicate_miss`
- `insufficient_evidence_high_verdict`

These labels are derived from retrieval success, oracle correctness, case type, lexical-only signals, and reviewed evidence sufficiency. They are evaluation-only diagnostics and are not used in the normal runtime path.

## Required Case Types

The curated set must cover:

- `clear_positive`
- `clear_negative`
- `borderline`
- `lexical_stress`
- `near_duplicate`
- `adjacent_distinct`
