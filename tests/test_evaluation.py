from app.config.settings import AppConfig, EvaluationConfig, PathConfig, RerankerConfig, RetrievalConfig, ScoringConfig
from app.evaluation.manual_eval import run_manual_evaluation
from app.ingest.indexer import build_sparse_index


def test_manual_evaluation_harness_generates_report(tmp_path) -> None:
    raw_path = PathConfig().raw_corpus_path
    processed_path = tmp_path / "processed.json"
    index_path = tmp_path / "index.json"
    report_path = tmp_path / "report.json"
    build_sparse_index(raw_path, processed_path, index_path)

    config = AppConfig(
        retrieval=RetrievalConfig(),
        reranker=RerankerConfig(),
        scoring=ScoringConfig(),
        evaluation=EvaluationConfig(default_modes=["sparse", "hybrid"]),
        paths=PathConfig(
            raw_corpus_path=raw_path,
            processed_corpus_path=processed_path,
            sparse_index_path=index_path,
            manual_eval_dir=PathConfig().manual_eval_dir,
            manual_eval_expectations_path=PathConfig().manual_eval_expectations_path,
            manual_eval_report_path=report_path,
        ),
    )

    report = run_manual_evaluation(config, output_path=report_path)

    assert report.cases
    assert report.summary["case_count"] == len(report.cases)
    assert report_path.exists()
    assert all(case.comparisons for case in report.cases)
