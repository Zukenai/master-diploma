from __future__ import annotations

from abc import ABC, abstractmethod

from app.config.settings import RerankerConfig
from app.schemas.idea import IdeaInput
from app.schemas.paper import RetrievedCandidate


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, idea: IdeaInput, candidates: list[RetrievedCandidate]) -> list[RetrievedCandidate]:
        raise NotImplementedError


class NoOpReranker(BaseReranker):
    def rerank(self, idea: IdeaInput, candidates: list[RetrievedCandidate]) -> list[RetrievedCandidate]:
        return candidates


class OverlapReranker(BaseReranker):
    def __init__(self, config: RerankerConfig):
        self.config = config

    def rerank(self, idea: IdeaInput, candidates: list[RetrievedCandidate]) -> list[RetrievedCandidate]:
        reranked: list[RetrievedCandidate] = []
        for candidate in candidates:
            source_scores = [
                score
                for score in [candidate.sparse_score, candidate.dense_score]
                if score is not None
            ]
            if source_scores:
                base_score = sum(source_scores) / len(source_scores)
                if candidate.fused_score is not None:
                    base_score = 0.8 * base_score + 0.2 * candidate.fused_score
            else:
                base_score = candidate.fused_score or candidate.score
            bonus = min(
                len(candidate.title_overlap_terms) * self.config.title_overlap_bonus
                + len(candidate.keyword_overlap_terms) * self.config.keyword_overlap_bonus
                + len(candidate.claim_overlap_terms) * self.config.keyword_overlap_bonus
                + len(candidate.matched_terms) * self.config.matched_term_bonus,
                self.config.max_bonus,
            )
            rerank_score = round(min(base_score + bonus, 1.0), 4)
            updated = candidate.model_copy(deep=True)
            updated.rerank_score = rerank_score
            updated.score = rerank_score
            updated.debug_signals.update(
                {
                    "reranker": self.config.strategy,
                    "rerank_bonus": round(bonus, 4),
                }
            )
            reranked.append(updated)
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked
