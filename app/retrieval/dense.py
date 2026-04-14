from __future__ import annotations

import json
from pathlib import Path

from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from app.config.settings import RetrievalConfig
from app.retrieval.base import BaseRetriever
from app.retrieval.query import build_query_text
from app.retrieval.signals import build_overlap_metadata
from app.schemas.idea import IdeaInput
from app.schemas.paper import PaperRecord, RetrievedCandidate


def _paper_text(paper: PaperRecord) -> str:
    return " ".join([paper.title, paper.abstract, *paper.keywords, *paper.claims])


class DenseRetriever(BaseRetriever):
    name = "dense"

    def __init__(self, processed_path: Path, config: RetrievalConfig):
        payload = json.loads(processed_path.read_text(encoding="utf-8"))
        self.papers = [PaperRecord.model_validate(item) for item in payload]
        self.config = config
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        document_matrix = self.vectorizer.fit_transform([_paper_text(paper) for paper in self.papers])

        max_components = min(
            config.dense_embedding_dims,
            max(document_matrix.shape[0] - 1, 1),
            max(document_matrix.shape[1] - 1, 1),
        )
        if max_components >= 2:
            self.svd = TruncatedSVD(n_components=max_components, random_state=42)
            dense_matrix = self.svd.fit_transform(document_matrix)
        else:
            self.svd = None
            dense_matrix = document_matrix.toarray()
        self.document_embeddings = normalize(dense_matrix)

    def _embed_query(self, idea: IdeaInput):
        query_matrix = self.vectorizer.transform([build_query_text(idea)])
        if self.svd is not None:
            query_matrix = self.svd.transform(query_matrix)
        else:
            query_matrix = query_matrix.toarray()
        return normalize(query_matrix)[0]

    def retrieve(self, idea: IdeaInput, top_k: int | None = None) -> list[RetrievedCandidate]:
        query_embedding = self._embed_query(idea)
        candidates: list[RetrievedCandidate] = []
        for paper, dense_vector in zip(self.papers, self.document_embeddings, strict=True):
            score = float(query_embedding @ dense_vector)
            overlap_metadata = build_overlap_metadata(idea, paper)
            if score < self.config.dense_min_score:
                continue
            if (
                overlap_metadata["matched_term_count"] < 3
                and overlap_metadata["title_overlap_count"] == 0
                and overlap_metadata["keyword_overlap_count"] == 0
            ):
                continue
            candidates.append(
                RetrievedCandidate(
                    paper=paper,
                    score=round(score, 4),
                    source_retrievers=[self.name],
                    dense_score=round(score, 4),
                    matched_terms=overlap_metadata["matched_terms"],
                    title_overlap_terms=overlap_metadata["title_overlap_terms"],
                    keyword_overlap_terms=overlap_metadata["keyword_overlap_terms"],
                    debug_signals={
                        "retriever": self.name,
                        "matched_term_count": overlap_metadata["matched_term_count"],
                        "title_overlap_count": overlap_metadata["title_overlap_count"],
                        "keyword_overlap_count": overlap_metadata["keyword_overlap_count"],
                    },
                )
            )
        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[: (top_k or self.config.top_k)]
