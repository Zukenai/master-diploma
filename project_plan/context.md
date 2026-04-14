# Project Context

## Thesis Topic

Official thesis topic:

`Agent-based AI system for automating scientific activity processes`

## Main Practical Contribution

The main practical and research contribution in this repository is a narrower module:

`literature-grounded prior-art risk assessment`

## What The Module Does

The module:

- accepts a structured description of a research idea
- retrieves relevant scientific publications
- estimates the risk that the idea substantially overlaps with existing literature
- returns a structured verdict with evidence and explanation

## What The Module Does Not Do

The module does not:

- prove absolute scientific novelty
- replace expert literature review
- operate over the entire global scholarly record
- act as an autonomous scientific judge

## Why This Formulation

The chosen formulation is `prior-art risk assessment`, not `absolute novelty detection`, because:

- novelty is context-dependent and difficult to verify absolutely
- risk estimation is more realistic and academically defensible
- the output can be explicitly grounded in retrieved evidence
- the approach remains reproducible under a known corpus and retrieval strategy

## Current Baseline

The current baseline is offline-first and local:

- small demo corpus
- sparse retrieval
- rule-based scoring
- template-based explanation

This provides a transparent baseline for later comparisons.
