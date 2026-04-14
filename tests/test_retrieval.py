from app.config.settings import get_config
from app.ingest.indexer import build_sparse_index
from app.retrieval.sparse import SparseRetriever
from app.schemas.idea import IdeaInput


def test_sparse_retrieval_returns_relevant_candidates(tmp_path) -> None:
    config = get_config()
    raw_path = config.paths.raw_corpus_path
    processed_path = tmp_path / "processed.json"
    index_path = tmp_path / "index.json"
    build_sparse_index(raw_path, processed_path, index_path)

    retriever = SparseRetriever(index_path, config.retrieval)
    idea = IdeaInput.model_validate(
        {
            "idea_id": "IDEA-RET",
            "title": "Risk assessment for overlap with scientific literature",
            "abstract": "An offline module retrieves papers, estimates overlap risk, and explains the verdict.",
            "keywords": ["overlap risk", "scientific literature"],
            "claims": ["ground the verdict in retrieved evidence"],
        }
    )

    results = retriever.retrieve(idea)

    assert results
    assert results[0].score >= results[-1].score
    assert any("risk" in term or "evidence" in term for term in results[0].matched_terms)
