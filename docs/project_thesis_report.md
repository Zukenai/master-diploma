# Project Thesis Report

## 1. Project identification and thesis positioning

### Official thesis topic

The official umbrella topic of the master's thesis is:

> «Агентная система на базе технологий искусственного интеллекта для автоматизации процессов научной деятельности»

### Actual implemented contribution

The repository does not implement a full autonomous scientific agent system. Its actual implemented and experimentally studied contribution is a narrower module:

**literature-grounded prior-art risk assessment for research ideas**

This narrowing is methodologically correct for the current repository because the implemented code, data, and experiments are concentrated around one bounded decision-support task:

- accept a structured research idea;
- retrieve related scholarly literature from a fixed local corpus;
- aggregate overlap evidence;
- produce a deterministic prior-art overlap risk verdict;
- expose the supporting evidence and an explanation.

### What the module does

The module estimates whether a proposed research idea appears to overlap with prior scholarly work **relative to a selected corpus and retrieval strategy**. It outputs a structured verdict:

- `high prior-art risk`
- `medium prior-art risk`
- `low prior-art risk`

The verdict is grounded in retrieved evidence and transparent overlap signals rather than in a black-box generative judge.

### What the module does not claim

The repository does **not** claim that it:

- detects absolute scientific novelty;
- performs exhaustive literature review over the whole scholarly web;
- implements a full “AI scientist” or end-to-end autonomous research system;
- provides production-scale scholarly infrastructure;
- replaces expert human novelty assessment.

The implemented claim is narrower and defensible: the system assesses prior-art overlap risk **under the current local corpus, retrieval configuration, and evaluation protocol**.

## 2. Executive technical summary of the repository

The repository is an **offline-first local research software package** for prior-art risk assessment. It contains:

- a small CLI application based on `typer`;
- data ingestion and indexing utilities for sample and curated corpora;
- three retrieval modes (`sparse`, `dense`, `hybrid`);
- a lightweight reranking layer;
- a deterministic evidence aggregation and scoring layer;
- deterministic explanation templates;
- two evaluation paths:
  - manual evaluation for early baseline comparison;
  - curated scholarly evaluation for thesis-grade experiments.

What can actually be run now:

- `sakana index-sample-corpus`
- `sakana acquire-curated-corpus`
- `sakana index-curated-corpus`
- `sakana assess-idea`
- `sakana evaluate-manual-cases`
- `sakana run-curated-experiment`

The repository boundary is clear. It is a compact experimental core, not a full product platform. The code supports local runtime assessment and local experiment generation, together with generated machine-readable and Markdown artifacts suitable for thesis writing.

## 3. Functional purpose of the module

### Input

The runtime input is a structured idea description represented by `IdeaInput` in [app/schemas/idea.py](../app/schemas/idea.py):

- `idea_id`
- `title`
- `abstract`
- `keywords`
- `claims`

### Processing stages

The module processes the input through the following stages:

1. validation of the idea schema;
2. corpus selection (`sample` or `curated`);
3. retrieval of related papers;
4. reranking of retrieved candidates;
5. aggregation of overlap evidence;
6. deterministic scoring and verdict assignment;
7. deterministic explanation generation.

### Output

The runtime output is `AssessmentResult` from [app/schemas/assessment.py](../app/schemas/assessment.py), containing:

- `risk_label`
- `risk_score`
- `evidence`
- `explanation`
- `debug`

### Interpretation of output

The output must be interpreted as a **corpus-bounded overlap risk assessment**:

- `high prior-art risk`: the current corpus contains evidence that is strong enough to treat the idea as substantially covered or near-duplicative;
- `medium prior-art risk`: the corpus contains meaningful but incomplete or scope-limited overlap;
- `low prior-art risk`: the corpus contains no prejudicial overlap, or only adjacent/non-sufficient related work.

The explanation summarizes the top evidence and overlap signals; it is not a free-form LLM judgement.

## 4. Repository architecture and code structure

### Configuration and settings

Central configuration is defined in [app/config/settings.py](../app/config/settings.py). It contains:

- `RetrievalConfig`
- `RerankerConfig`
- `ScoringConfig`
- `EvaluationConfig`
- `PathConfig`
- `AppConfig`

`PathConfig` separates sample and curated assets, while `with_corpus_paths(...)` switches runtime paths between corpus modes without changing the rest of the pipeline.

### CLI entrypoints

The CLI lives in [app/cli/main.py](../app/cli/main.py). It exposes the repository’s operational entrypoints:

- indexing commands;
- curated corpus acquisition;
- idea assessment;
- manual evaluation;
- curated experiment.

This file is the main user-facing runtime interface.

### Pipeline orchestration

The end-to-end runtime pipeline is implemented in [app/pipeline/assess.py](../app/pipeline/assess.py), in `PriorArtAssessmentPipeline`. The class wires together:

- retriever construction;
- reranker selection;
- scoring;
- explanation generation.

### Retrieval layer

The retrieval layer lives in `app/retrieval/`:

- [app/retrieval/base.py](../app/retrieval/base.py): abstract retriever contract;
- [app/retrieval/factory.py](../app/retrieval/factory.py): strategy selection;
- [app/retrieval/sparse.py](../app/retrieval/sparse.py): lexical TF-IDF-like retrieval;
- [app/retrieval/dense.py](../app/retrieval/dense.py): local dense-like retrieval using TF-IDF + SVD;
- [app/retrieval/hybrid.py](../app/retrieval/hybrid.py): reciprocal-rank fusion over sparse and dense;
- [app/retrieval/signals.py](../app/retrieval/signals.py): overlap-signal extraction.

### Reranking layer

The reranking layer is in [app/rerank/base.py](../app/rerank/base.py). It currently includes:

- `NoOpReranker`
- `OverlapReranker`

The active reranker is still lightweight, but it is real code and not merely a placeholder.

### Scoring and verdict layer

The verdict logic is in [app/scoring/rules.py](../app/scoring/rules.py). This is the core deterministic judgement layer. It computes:

- numeric risk score;
- evidence-state diagnostics;
- final low/medium/high verdict;
- debug fields used by the experiment pipeline.

### Explanation layer

The deterministic explanation lives in [app/explanation/templates.py](../app/explanation/templates.py). It creates an explanation from the verdict, score, and evidence items, without invoking any LLM judge.

### Evaluation layer

Evaluation lives in `app/evaluation/`:

- [app/evaluation/manual_eval.py](../app/evaluation/manual_eval.py): early repeatable manual comparison harness;
- [app/evaluation/curated_experiment.py](../app/evaluation/curated_experiment.py): current thesis-grade curated experiment runner with separated evaluation layers.

### Data, evaluation assets, and generated artifacts

The repository separates data and generated outputs:

- `data/raw/`: raw sample and curated corpus files;
- `data/indexes/`: sparse indexes;
- `data/processed/`: generated reports and normalized corpora;
- `data/eval/`: expectation and evaluation metadata;
- `scripts/curated_eval/`: curated case inputs;
- `docs/`: protocol and architecture documentation;
- `project_plan/`: iteration/result tracking for the thesis workflow.

### Compact repository map

- `app/`: runtime and evaluation code
- `data/raw/`: source corpora
- `data/eval/`: evaluation annotations
- `data/processed/`: generated report artifacts
- `docs/`: technical and protocol documentation
- `project_plan/`: thesis iteration tracking
- `tests/`: regression and experiment tests

## 5. End-to-end pipeline description

The current processing pipeline works as follows.

### Step 1. Idea input

The user provides an idea JSON file. The CLI command `sakana assess-idea` reads it and validates it through `IdeaInput`.

### Step 2. Validation and schema handling

Validation is done with `pydantic`. Empty keyword/claim strings are normalized out in `IdeaInput.strip_values(...)`.

### Step 3. Corpus selection

The runtime can operate on:

- `sample` corpus
- `curated` corpus

Path switching is handled by `with_corpus_paths(...)` in [app/config/settings.py](../app/config/settings.py).

### Step 4. Retrieval

`PriorArtAssessmentPipeline` builds the selected retriever through `build_retriever(...)`. Depending on the mode, this can be:

- `SparseRetriever`
- `DenseRetriever`
- `HybridRetriever`

### Step 5. Reranking

Retrieved candidates are passed through `OverlapReranker` (or `NoOpReranker`, depending on config). Reranking adjusts candidate scores with explicit overlap bonuses rather than learned models.

### Step 6. Evidence aggregation

The top candidates are converted into `EvidenceItem` records containing:

- paper identifiers and titles;
- retriever provenance;
- sparse/dense/fused/rerank scores where available;
- overlap signals and rationale.

### Step 7. Scoring and verdict assignment

The scoring layer computes aggregate overlap features and then maps them into:

- a bounded numeric `risk_score`
- a final risk label
- detailed debug diagnostics

### Step 8. Explanation generation

`build_explanation(...)` produces a deterministic textual explanation of:

- top overlapping papers;
- retrieval source provenance;
- overlap signal summary.

### Step 9. Final assessment result

The pipeline returns a structured `AssessmentResult`, which the CLI emits as JSON.

## 6. Retrieval and evidence logic

### Retrieval modes

The repository currently implements three retrieval modes:

1. **Sparse**
   - TF-IDF-like scoring over tokenized local text;
   - query tokens are built from title, abstract, keywords, and claims;
   - title and keyword boosts are applied in the query vector.

2. **Dense**
   - local vector-space retrieval using `TfidfVectorizer` followed by `TruncatedSVD`;
   - documents and queries are normalized and compared through dot product;
   - low-signal candidates are filtered out using overlap metadata checks.

3. **Hybrid**
   - reciprocal-rank fusion over sparse and dense candidate lists;
   - merged candidates preserve source provenance and combined overlap metadata.

### Reranking behavior

The current `OverlapReranker` recomputes the effective score by:

- averaging sparse/dense source scores when available;
- blending fused score if present;
- adding bounded bonuses for title, keyword, claim, and matched-term overlap.

This keeps reranking transparent and lightweight.

### Evidence representation

Runtime evidence uses `EvidenceItem`, while retrieval internally uses `RetrievedCandidate`. Evidence contains:

- paper metadata;
- retriever provenance;
- score fields;
- overlap-signal dictionaries;
- human-readable rationale strings.

### Overlap signals used

The current overlap logic in [app/retrieval/signals.py](../app/retrieval/signals.py) computes:

- `matched_terms`
- `title_overlap_terms`
- `keyword_overlap_terms`
- `claim_overlap_terms`
- count versions of the same
- `facet_overlap_count`

These signals are passed into both retrieval/reranking and verdict logic.

### How evidence feeds into verdict logic

The scoring layer aggregates evidence across the top candidates through features such as:

- `max_similarity`
- `avg_top_similarity`
- `count_above_threshold`
- aggregate title / keyword / claim overlap
- `facet_coverage`
- `multi_source_ratio`
- `strong_support_count`
- `shallow_support_count`
- `lexical_only_count`
- `weak_support_count`

These are then interpreted through an evidence-state rubric before the final label is assigned.

## 7. Verdict and scoring methodology

### Risk score concept

The system still computes a numeric `risk_score` as a weighted combination of similarity and overlap features. This score is useful as a continuous diagnostic signal, but it is no longer treated as sufficient by itself for the final `high` verdict.

### Baseline label thresholds

The code still computes a raw threshold-based label via `_risk_label(...)` in [app/scoring/rules.py](../app/scoring/rules.py):

- `>= high_risk_score` -> `high`
- `>= medium_risk_score` -> `medium`
- else -> `low`

However, this raw label is now only an intermediate value.

### Evidence-state-driven logic

The current implemented verdict logic derives an explicit evidence-state rubric in `_derive_evidence_state(...)`:

- `self_sufficient`
- `combination_sufficient`
- `partial`
- `adjacent_only`

It also computes:

- `scope_narrowing_required`
- `high_blocked_by_insufficiency`
- `evidence_state_basis`

### Meaning of the evidence states

- `self_sufficient`: one or more evidence items show enough claim/title/facet overlap to justify a high-risk judgement directly.
- `combination_sufficient`: multiple pieces of evidence jointly justify a high-risk judgement.
- `partial`: overlap is meaningful but incomplete or insufficiently broad, so the defensible result is medium.
- `adjacent_only`: evidence is related or semantically adjacent, but not prejudicial enough to move above low.

`scope_narrowing_required` indicates that the evidence appears to support only a narrower or more specific variant of the idea than the full input claim.

### Final verdict mapping

The final label mapping is now evidence-state-driven:

- `high prior-art risk` only for `self_sufficient` or `combination_sufficient` evidence without scope narrowing;
- `medium prior-art risk` for `partial` overlap;
- `low prior-art risk` for `adjacent_only`.

### Why this is more defensible than raw thresholding

This change makes the system more academically defensible because:

- `medium` is no longer just a leftover numeric interval;
- high similarity alone is not enough for a `high` verdict;
- borderline cases with strong but incomplete support are explicitly modeled as `partial`;
- adjacent but distinct work can be capped at `low` rather than escalated by raw score.

This is especially important for the thesis because the remaining errors are mostly ordinal over-escalation errors rather than complete retrieval failure.

## 8. Evaluation framework

The current curated evaluation framework is implemented in [app/evaluation/curated_experiment.py](../app/evaluation/curated_experiment.py). It explicitly separates three layers:

### Retrieval evaluation

This layer evaluates whether the system surfaces the expected prior-art evidence. It reports:

- positive hit@3-like success;
- negative-case clearing;
- retrieval success rate;
- grouped breakdown by case type.

### Oracle-verdict evaluation

This layer bypasses normal retrieval and feeds curated oracle evidence into the verdict logic. It answers:

> If the system is given the intended evidence, does the verdict logic behave correctly?

This isolates verdict-calibration quality from retrieval quality.

### End-to-end evaluation

This layer runs the full pipeline:

- retrieval
- reranking
- admissibility filtering
- verdict assignment

It answers:

> How does the full implemented system behave in practice?

### Why the layers are separated

This separation is methodologically important because it distinguishes:

- retrieval-side misses,
- verdict-side calibration problems,
- full pipeline behavior.

Without this separation, it would be impossible to say whether an error comes from failure to retrieve the right evidence or from failure to interpret good evidence correctly.

### Curated evaluation assets

The curated evaluation uses:

- a small curated scholarly corpus;
- curated case JSON inputs in `scripts/curated_eval/`;
- expectation metadata in `data/eval/curated_experiment_expectations.json`;
- generated JSON and Markdown reports in `data/processed/`.

### Curated evaluation metadata

Current expectation records include fields such as:

- `case_id`
- `expected_risk`
- `expected_relevant_paper_ids`
- `oracle_evidence_ids`
- `case_type`
- `annotation_rationale`
- `cutoff_year`
- `initial_label`
- `review_label`
- `adjudicated_label`
- `initial_case_type`
- `review_case_type`
- `oracle_evidence_sufficiency`

### Case taxonomy

The curated taxonomy currently includes:

- `clear_positive`
- `clear_negative`
- `borderline`
- `lexical_stress`
- `near_duplicate`
- `adjacent_distinct`

### Diagnostics and failure typing

The experiment runner emits deterministic diagnostics per case and mode, including:

- oracle and end-to-end verdicts;
- risk scores;
- evidence ids;
- feature values;
- triggered decision summary.

Failure types are assigned deterministically through a compact taxonomy including:

- `ok`
- `retrieval_miss`
- `oracle_wrong`
- `lexical_overfire`
- `borderline_underfire`
- `near_duplicate_miss`
- `insufficient_evidence_high_verdict`

### Temporal admissibility

Curated evaluation also applies a lightweight temporal admissibility rule:

- each case has `cutoff_year`;
- evidence published after the cutoff is treated as inadmissible for evaluation;
- the runtime pipeline itself is not globally time-constrained, but the evaluation logic is.

This makes the experiments more defensible without turning the repository into a heavy temporal reasoning system.

## 9. Current experimental assets

Based on the current repository state and the latest generated report:

- curated scholarly corpus size: **10 documents**
- curated case count: **12 cases**
- oracle annotation coverage: **12/12**

Current case-type distribution:

- `near_duplicate`: 2
- `borderline`: 4
- `clear_negative`: 1
- `lexical_stress`: 2
- `clear_positive`: 1
- `adjacent_distinct`: 2

Review/adjudication layer:

- labels changed on review: 3
- case types changed on review: 1
- oracle evidence sufficiency judgements changed on review: 3

Current generated experiment assets:

- [data/processed/curated_experiment_report.json](../data/processed/curated_experiment_report.json)
- [data/processed/curated_experiment_notes.md](../data/processed/curated_experiment_notes.md)

These artifacts already contain:

- dataset summary
- retrieval results
- oracle-verdict results
- end-to-end results
- diagnostics and failure breakdown
- calibration summary
- before/after comparison

## 10. Current results

The following numbers are taken from the current generated report, not from an earlier iteration snapshot.

### Retrieval results by mode

- `sparse`
  - positive hit@3: `9/9`
  - negative clear: `1/3`
  - retrieval success rate: `0.8333`

- `dense`
  - positive hit@3: `9/9`
  - negative clear: `0/3`
  - retrieval success rate: `0.75`

- `hybrid`
  - positive hit@3: `9/9`
  - negative clear: `0/3`
  - retrieval success rate: `0.75`

### Oracle-verdict results

- accuracy: `1.0`
- macro-F1: `1.0`
- mean ordinal error: `0.0`
- medium-risk match rate: `1.0`
- borderline-case match rate: `1.0`

This means that under the current curated oracle evidence, the verdict logic matches all current adjudicated labels.

### End-to-end results

- `sparse`
  - accuracy: `0.9167`
  - macro-F1: `0.9259`
  - mean ordinal error: `0.0833`
  - mismatch cases: `["CURATED-012"]`

- `dense`
  - accuracy: `0.8333`
  - macro-F1: `0.85`
  - mean ordinal error: `0.1667`
  - mismatch cases: `["CURATED-008", "CURATED-012"]`

- `hybrid`
  - accuracy: `0.8333`
  - macro-F1: `0.85`
  - mean ordinal error: `0.1667`
  - mismatch cases: `["CURATED-008", "CURATED-012"]`

### Ordinal-aware interpretation

The current residual errors are **ordinal**:

- no remaining end-to-end case collapses into an obviously wrong `high` verdict on the curated set;
- the remaining misses are low-to-medium over-escalations on adjacent or lexical-stress cases.

### What improved after the final calibration pass

The current implementation introduced evidence-state-driven verdict assignment. In the current generated report:

- oracle verdict errors on borderline and adjacent-distinct cases were removed;
- medium-risk and borderline-case oracle match rates reached `1.0`;
- end-to-end borderline performance is now `1.0` for all three modes;
- remaining misses are concentrated in low-risk adjacent/lexical cases rather than in medium/high collapse behavior.

## 11. Interpretation of results

### What is currently strong

- The repository already contains a real, executable end-to-end module.
- Retrieval, verdict, and end-to-end behavior are evaluated separately.
- The core verdict logic is transparent and deterministic.
- Oracle-verdict performance under the current curated setup is strong.
- The repository supports both runtime use and thesis-grade experimental reporting.

### What is moderately strong

- Retrieval is strong on positive cases but still imperfect on negative clearing.
- Sparse performs better conservatively on negatives, while dense/hybrid remain more aggressive.
- The evaluation design is credible for a compact thesis experiment, but still small-scale.

### What remains weak

- Dense and hybrid still over-escalate some low-risk adjacent or lexical-stress cases into `medium`.
- The curated corpus remains narrow and intentionally compact.
- Runtime retrieval is still not temporally constrained, even though evaluation is.

### What the results prove

The current results support a bounded thesis claim:

- a local, deterministic, evidence-grounded module for corpus-bounded prior-art risk assessment has been implemented and experimentally evaluated;
- its decision quality can be analyzed separately from retrieval quality;
- its current logic is adequate for a compact thesis-scale experimental core.

### What the results do not prove

The results do **not** prove that:

- the system performs universal novelty assessment;
- the curated corpus is exhaustive;
- the method generalizes without qualification to all scientific domains;
- the repository constitutes a full AI-based agent system for all scientific activity.

## 12. Current limitations

The current repository has real limitations that should be presented honestly in the thesis.

### Compact curated setup

The curated setup is deliberately small:

- 10 curated documents
- 12 curated evaluation cases

This is appropriate for a compact experimental study, but not for broad benchmark claims.

### Bounded corpus

All verdicts are relative to the selected corpus snapshot. If relevant literature is missing from the local corpus, the system cannot recover it at runtime.

### Remaining retrieval-side errors

The remaining end-to-end errors are retrieval/evidence-composition sensitive:

- `CURATED-008`
- `CURATED-012`

These are not oracle-layer failures, which means the current residual weakness is mainly in end-to-end retrieval realism rather than in the verdict rubric itself.

### Domain narrowness

The corpus and evaluation set are domain-focused around prior-art, novelty, literature overlap, and adjacent scholarly workflow themes. This improves experiment control but limits breadth.

### Runtime vs evaluation path differences

Evaluation uses:

- oracle evidence annotations
- review/adjudicated labels
- temporal admissibility

These are explicitly evaluation-only assets. The normal runtime path does not depend on them.

### No claim of absolute novelty detection

This is a central limitation and should be stated explicitly in the thesis:

the repository implements **prior-art overlap risk assessment**, not an absolute novelty detector.

## 13. Mapping to the planned VKR structure

### Chapter 1: review and problem statement

The following repository materials support the review and motivation chapter:

- [docs/curated_corpus.md](curated_corpus.md)
- [docs/experimental_protocol.md](experimental_protocol.md)
- [docs/evaluation_annotation_protocol.md](evaluation_annotation_protocol.md)
- curated corpus provenance and manifest in `data/provenance/`

These materials help explain the problem context, why prior-art overlap screening matters, and why a corpus-bounded experimental approach is appropriate.

### Chapter 2: requirements and formal problem statement

The repository supports Chapter 2 through:

- input/output schemas in `app/schemas/`
- configuration in `app/config/settings.py`
- CLI and pipeline boundaries in `app/cli/main.py` and `app/pipeline/assess.py`
- explicit label protocol and case taxonomy in the evaluation metadata

These are enough to formalize the problem as a structured decision-support task.

### Chapter 3: architecture and implementation

The strongest support for Chapter 3 is already implemented in code:

- retrieval layer in `app/retrieval/`
- reranking in `app/rerank/`
- scoring in `app/scoring/`
- pipeline orchestration in `app/pipeline/`
- explanation generation in `app/explanation/`
- CLI entrypoints in `app/cli/`

This is the core implementation chapter material.

### Chapter 4: experiments and results

Chapter 4 is supported by:

- curated evaluation assets in `scripts/curated_eval/` and `data/eval/`
- experiment runner in `app/evaluation/curated_experiment.py`
- generated reports in `data/processed/`
- review/adjudication metadata
- temporal admissibility logic
- failure typing and diagnostics

This chapter can be built largely from already existing repository artifacts and their interpretation.

### Chapter 5: commercialization / practical relevance

The repository supports Chapter 5 mainly through practical positioning:

- local reproducible runtime;
- low infrastructure complexity;
- transparent evidence-grounded output;
- potential usefulness for early-stage research planning, proposal screening, and innovation support workflows.

This is an argument for practical relevance, not proof of a production-ready platform.

## 14. What is already sufficient for the thesis and what still requires writing only

### Already implemented in code and artifacts

- runnable assessment pipeline
- sample and curated corpus support
- sparse/dense/hybrid retrieval
- reranking
- deterministic scoring and explanation
- evidence-state-driven verdict logic
- curated evaluation protocol
- oracle and end-to-end experiment layers
- diagnostics and generated reports

### Mostly requires thesis writing, interpretation, and tables

- narrative explanation of the problem setting
- chapter-level architectural exposition
- experiment tables and figure formatting
- interpretation of oracle vs end-to-end results
- explicit discussion of practical relevance and bounded applicability

### Better presented as future work rather than new coding

- broader corpus coverage
- domain expansion
- stronger negative-case retrieval realism
- more realistic large-scale benchmark construction
- integration into a broader agent system for scientific process automation

These items no longer require immediate implementation to defend the current thesis core.

## 15. Concise final status statement

The repository currently implements a **local, reproducible, evidence-grounded module for corpus-bounded prior-art risk assessment of research ideas**. Its main contribution is a deterministic retrieval → evidence → verdict pipeline together with a compact but methodologically explicit evaluation framework that separates retrieval quality, oracle-verdict quality, and end-to-end behavior. Its main limitation is the compact and domain-focused curated setup, which constrains scale and generality. Nevertheless, as a master’s thesis core, the repository is sufficient and defensible because it contains a real implemented system, real experiment artifacts, transparent methodology, and bounded, honestly interpretable results.
