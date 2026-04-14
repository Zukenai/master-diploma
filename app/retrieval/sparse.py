from __future__ import annotations

import json
import math
from pathlib import Path

from app.config.settings import RetrievalConfig
from app.retrieval.base import BaseRetriever
from app.retrieval.query import build_query_text
from app.schemas.idea import IdeaInput
from app.schemas.paper import PaperRecord, RetrievedCandidate
from app.utils.text import compute_overlap_terms, cosine_similarity, term_frequency, tokenize


class SparseRetriever(BaseRetriever):
    def __init__(self, index_path: Path, config: RetrievalConfig):
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        self.document_count = payload["document_count"]
        self.documents = payload["documents"]
        self.document_frequency = payload["document_frequency"]
        self.config = config

    def _query_vector(self, idea: IdeaInput) -> tuple[dict[str, float], list[str], list[str], list[str]]:
        query_tokens = tokenize(build_query_text(idea))
        title_tokens = tokenize(idea.title)
        keyword_tokens = [token for keyword in idea.keywords for token in tokenize(keyword)]
        tf = term_frequency(query_tokens)
        query_vector: dict[str, float] = {}
        for token, tf_value in tf.items():
            doc_freq = self.document_frequency.get(token, 0)
            idf = math.log((1 + self.document_count) / (1 + doc_freq)) + 1
            boosted = tf_value * idf
            if token in title_tokens:
                boosted *= self.config.title_boost
            if token in keyword_tokens:
                boosted *= self.config.keyword_boost
            query_vector[token] = round(boosted, 6)
        return query_vector, query_tokens, title_tokens, keyword_tokens

    def retrieve(self, idea: IdeaInput) -> list[RetrievedCandidate]:
        query_vector, query_tokens, title_tokens, keyword_tokens = self._query_vector(idea)
        candidates: list[RetrievedCandidate] = []

        for entry in self.documents:
            score = cosine_similarity(query_vector, entry["tfidf"])
            if score < self.config.min_score:
                continue
            paper = PaperRecord.model_validate(entry["paper"])
            matched_terms = compute_overlap_terms(query_tokens, entry["tokens"])
            title_overlap_terms = compute_overlap_terms(title_tokens, entry["title_tokens"])
            candidate_keyword_terms = entry["keyword_tokens"]
            keyword_overlap_terms = compute_overlap_terms(keyword_tokens, candidate_keyword_terms)
            candidates.append(
                RetrievedCandidate(
                    paper=paper,
                    score=round(score, 4),
                    matched_terms=matched_terms[:10],
                    title_overlap_terms=title_overlap_terms[:8],
                    keyword_overlap_terms=keyword_overlap_terms[:8],
                )
            )

        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[: self.config.top_k]
