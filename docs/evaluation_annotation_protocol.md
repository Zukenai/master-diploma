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
- `annotation_rationale`

## Required Case Types

The curated set must cover:

- `clear_positive`
- `clear_negative`
- `borderline`
- `lexical_stress`
- `near_duplicate`
- `adjacent_distinct`
