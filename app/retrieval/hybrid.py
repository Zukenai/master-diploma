from __future__ import annotations

from collections import defaultdict

from app.config.settings import RetrievalConfig
from app.retrieval.base import BaseRetriever
from app.schemas.idea import IdeaInput
from app.schemas.paper import RetrievedCandidate


class HybridRetriever(BaseRetriever):
    name = "hybrid"

    def __init__(self, sparse_retriever: BaseRetriever, dense_retriever: BaseRetriever, config: RetrievalConfig):
        self.sparse_retriever = sparse_retriever
        self.dense_retriever = dense_retriever
        self.config = config

    def retrieve(self, idea: IdeaInput, top_k: int | None = None) -> list[RetrievedCandidate]:
        limit = top_k or self.config.top_k
        pool_size = max(limit, self.config.candidate_pool_size)
        sparse_candidates = self.sparse_retriever.retrieve(idea, top_k=pool_size)
        dense_candidates = self.dense_retriever.retrieve(idea, top_k=pool_size)

        fused_scores: defaultdict[str, float] = defaultdict(float)
        merged_candidates: dict[str, RetrievedCandidate] = {}

        for rank, candidate in enumerate(sparse_candidates, start=1):
            contribution = 1 / (self.config.fusion_constant + rank)
            paper_id = candidate.paper.paper_id
            fused_scores[paper_id] += contribution
            merged_candidates[paper_id] = candidate.model_copy(deep=True)

        for rank, candidate in enumerate(dense_candidates, start=1):
            contribution = 1 / (self.config.fusion_constant + rank)
            paper_id = candidate.paper.paper_id
            fused_scores[paper_id] += contribution
            if paper_id in merged_candidates:
                existing = merged_candidates[paper_id]
                existing.source_retrievers = sorted(set(existing.source_retrievers + candidate.source_retrievers))
                existing.dense_score = candidate.dense_score
                existing.matched_terms = sorted(set(existing.matched_terms + candidate.matched_terms))[:10]
                existing.title_overlap_terms = sorted(
                    set(existing.title_overlap_terms + candidate.title_overlap_terms)
                )[:8]
                existing.keyword_overlap_terms = sorted(
                    set(existing.keyword_overlap_terms + candidate.keyword_overlap_terms)
                )[:8]
                existing.claim_overlap_terms = sorted(
                    set(existing.claim_overlap_terms + candidate.claim_overlap_terms)
                )[:8]
            else:
                merged_candidates[paper_id] = candidate.model_copy(deep=True)

        max_fused_score = max(fused_scores.values(), default=1.0)
        fused_candidates: list[RetrievedCandidate] = []
        for paper_id, candidate in merged_candidates.items():
            normalized_fused_score = round(fused_scores[paper_id] / max_fused_score, 4)
            candidate.fused_score = normalized_fused_score
            candidate.score = normalized_fused_score
            candidate.source_retrievers = sorted(set(candidate.source_retrievers + [self.name]))
            candidate.debug_signals.update(
                {
                    "retriever": self.name,
                    "fused_score": normalized_fused_score,
                    "facet_overlap_count": sum(
                        1
                        for overlap_terms in [
                            candidate.title_overlap_terms,
                            candidate.keyword_overlap_terms,
                            candidate.claim_overlap_terms,
                        ]
                        if overlap_terms
                    ),
                }
            )
            fused_candidates.append(candidate)

        fused_candidates.sort(key=lambda item: item.score, reverse=True)
        return fused_candidates[:limit]
