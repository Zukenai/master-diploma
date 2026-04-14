from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.idea import IdeaInput
from app.schemas.paper import RetrievedCandidate


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, idea: IdeaInput, candidates: list[RetrievedCandidate]) -> list[RetrievedCandidate]:
        raise NotImplementedError


class NoOpReranker(BaseReranker):
    def rerank(self, idea: IdeaInput, candidates: list[RetrievedCandidate]) -> list[RetrievedCandidate]:
        return candidates
