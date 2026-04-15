import json

from app.config.settings import AppConfig, EvaluationConfig, PathConfig, RerankerConfig, RetrievalConfig, ScoringConfig
from app.evaluation.curated_experiment import run_curated_experiment
from app.ingest.indexer import build_sparse_index


def test_curated_experiment_generates_separate_observation_sections(tmp_path) -> None:
    raw_records = [
        {
            "paper_id": "C001",
            "title": "Prior art search for claims",
            "abstract": "This paper studies claim-aware prior art search and overlap signals.",
            "keywords": ["prior art", "claims"],
            "claims": ["claim-aware prior art search"],
            "year": 2022,
            "venue": "Test Venue",
        },
        {
            "paper_id": "C002",
            "title": "Scientific literature retrieval benchmark",
            "abstract": "This work benchmarks scientific literature retrieval.",
            "keywords": ["literature retrieval"],
            "claims": ["retrieval benchmark"],
            "year": 2024,
            "venue": "Test Venue",
        },
    ]
    curated_raw = tmp_path / "curated.json"
    curated_processed = tmp_path / "curated_processed.json"
    curated_index = tmp_path / "curated_index.json"
    eval_dir = tmp_path / "eval_cases"
    expectations_path = tmp_path / "expectations.json"
    report_path = tmp_path / "report.json"
    notes_path = tmp_path / "notes.md"
    eval_dir.mkdir()

    curated_raw.write_text(json.dumps(raw_records), encoding="utf-8")
    (eval_dir / "case.json").write_text(
        json.dumps(
            {
                "idea_id": "CASE-1",
                "title": "Claim-aware overlap risk",
                "abstract": "Assess claim-aware prior art overlap risk with literature evidence.",
                "keywords": ["prior art", "claims"],
                "claims": ["claim-aware prior art search"],
            }
        ),
        encoding="utf-8",
    )
    expectations_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "CASE-1",
                    "expected_risk": "high prior-art risk",
                    "expected_relevant_paper_ids": ["C001"],
                    "oracle_evidence_ids": ["C001"],
                    "case_type": "clear_positive",
                    "annotation_rationale": "Direct curated overlap.",
                }
            ]
        ),
        encoding="utf-8",
    )
    build_sparse_index(curated_raw, curated_processed, curated_index)

    config = AppConfig(
        retrieval=RetrievalConfig(top_k=2),
        reranker=RerankerConfig(),
        scoring=ScoringConfig(),
        evaluation=EvaluationConfig(default_modes=["sparse"]),
        paths=PathConfig(
            curated_raw_corpus_path=curated_raw,
            curated_processed_corpus_path=curated_processed,
            curated_sparse_index_path=curated_index,
            curated_eval_dir=eval_dir,
            curated_eval_expectations_path=expectations_path,
            curated_experiment_report_path=report_path,
            curated_experiment_notes_path=notes_path,
        ),
    )

    report = run_curated_experiment(config, output_path=report_path, notes_path=notes_path)

    assert report["corpus_summary"]["document_count"] == 2
    assert report["retrieval_evaluation"]["observations"]
    assert report["oracle_verdict_evaluation"]["summary"]["accuracy"] >= 0.0
    assert report["end_to_end_verdict_evaluation"]["observations"]
    assert report["dataset_summary"]["case_type_distribution"]["clear_positive"] == 1
    assert report["limitation_notes"]
    assert report_path.exists()
    assert notes_path.exists()


def test_curated_experiment_reports_before_after_comparison(tmp_path) -> None:
    raw_records = [
        {
            "paper_id": "C001",
            "title": "Prior art search for claims",
            "abstract": "This paper studies claim-aware prior art search and overlap signals.",
            "keywords": ["prior art", "claims"],
            "claims": ["claim-aware prior art search"],
            "year": 2022,
            "venue": "Test Venue",
        }
    ]
    curated_raw = tmp_path / "curated.json"
    curated_processed = tmp_path / "curated_processed.json"
    curated_index = tmp_path / "curated_index.json"
    eval_dir = tmp_path / "eval_cases"
    expectations_path = tmp_path / "expectations.json"
    report_path = tmp_path / "report.json"
    notes_path = tmp_path / "notes.md"
    eval_dir.mkdir()

    curated_raw.write_text(json.dumps(raw_records), encoding="utf-8")
    (eval_dir / "case.json").write_text(
        json.dumps(
            {
                "idea_id": "CASE-1",
                "title": "Claim-aware overlap risk",
                "abstract": "Assess claim-aware prior art overlap risk with literature evidence.",
                "keywords": ["prior art", "claims"],
                "claims": ["claim-aware prior art search"],
            }
        ),
        encoding="utf-8",
    )
    expectations_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "CASE-1",
                    "expected_risk": "high prior-art risk",
                    "expected_relevant_paper_ids": ["C001"],
                    "oracle_evidence_ids": ["C001"],
                    "case_type": "near_duplicate",
                    "annotation_rationale": "Direct curated overlap.",
                }
            ]
        ),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(
            {
                "run_configuration": {"modes": ["sparse"]},
                "cases": [
                    {
                        "case_id": "CASE-1",
                        "comparisons": [
                            {
                                "mode": "sparse",
                                "risk_label": "low prior-art risk",
                                "risk_score": 0.2,
                                "verdict_matches_expectation": False,
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    build_sparse_index(curated_raw, curated_processed, curated_index)

    config = AppConfig(
        retrieval=RetrievalConfig(top_k=2),
        reranker=RerankerConfig(),
        scoring=ScoringConfig(),
        evaluation=EvaluationConfig(default_modes=["sparse"]),
        paths=PathConfig(
            curated_raw_corpus_path=curated_raw,
            curated_processed_corpus_path=curated_processed,
            curated_sparse_index_path=curated_index,
            curated_eval_dir=eval_dir,
            curated_eval_expectations_path=expectations_path,
            curated_experiment_report_path=report_path,
            curated_experiment_notes_path=notes_path,
        ),
    )

    report = run_curated_experiment(config, output_path=report_path, notes_path=notes_path)

    assert report["before_after_comparison"] is not None
    assert report["before_after_comparison"]["mode_deltas"]["sparse"]["shared_case_count"] == 1
