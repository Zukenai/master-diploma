from app.config.settings import get_config
from app.ingest.indexer import build_sparse_index
from app.retrieval.dense import DenseRetriever
from app.retrieval.hybrid import HybridRetriever
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


def test_dense_retrieval_returns_candidates(tmp_path) -> None:
    config = get_config()
    raw_path = config.paths.raw_corpus_path
    processed_path = tmp_path / "processed.json"
    index_path = tmp_path / "index.json"
    build_sparse_index(raw_path, processed_path, index_path)

    retriever = DenseRetriever(processed_path, config.retrieval)
    idea = IdeaInput.model_validate(
        {
            "idea_id": "IDEA-DENSE",
            "title": "Screening research ideas with literature overlap evidence",
            "abstract": "A local module retrieves related papers and estimates overlap risk with explainable evidence.",
            "keywords": ["research ideas", "overlap evidence"],
            "claims": ["support transparent screening"],
        }
    )

    results = retriever.retrieve(idea)

    assert results
    assert results[0].dense_score is not None
    assert "dense" in results[0].source_retrievers


def test_hybrid_retrieval_exposes_fused_scores(tmp_path) -> None:
    config = get_config()
    raw_path = config.paths.raw_corpus_path
    processed_path = tmp_path / "processed.json"
    index_path = tmp_path / "index.json"
    build_sparse_index(raw_path, processed_path, index_path)

    sparse = SparseRetriever(index_path, config.retrieval)
    dense = DenseRetriever(processed_path, config.retrieval)
    retriever = HybridRetriever(sparse, dense, config.retrieval)
    idea = IdeaInput.model_validate(
        {
            "idea_id": "IDEA-HYBRID",
            "title": "Claim-aware novelty risk screening",
            "abstract": "The system uses claim-aware retrieval and evidence signals to assess overlap with prior work.",
            "keywords": ["claim-aware retrieval", "novelty risk"],
            "claims": ["screen technical ideas against prior work"],
        }
    )

    results = retriever.retrieve(idea)

    assert results
    assert results[0].fused_score is not None
    assert "hybrid" in results[0].source_retrievers
