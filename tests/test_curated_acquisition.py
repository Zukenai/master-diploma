from app.config.settings import AppConfig, PathConfig, with_corpus_paths
from app.ingest.curated_acquisition import _reconstruct_abstract


def test_reconstruct_abstract_from_inverted_index() -> None:
    abstract = _reconstruct_abstract(
        {
            "Prior": [0],
            "art": [1],
            "search": [2],
            "matters.": [3],
        }
    )

    assert abstract == "Prior art search matters."


def test_with_corpus_paths_switches_to_curated_paths() -> None:
    config = AppConfig()
    curated = with_corpus_paths(config, "curated")

    assert curated.paths.raw_corpus_path == PathConfig().curated_raw_corpus_path
    assert curated.paths.processed_corpus_path == PathConfig().curated_processed_corpus_path
    assert curated.paths.sparse_index_path == PathConfig().curated_sparse_index_path
