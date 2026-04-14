from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.idea import IdeaInput
from app.schemas.paper import RetrievedCandidate


class BaseRetriever(ABC):
    name: str

    @abstractmethod
    def retrieve(self, idea: IdeaInput, top_k: int | None = None) -> list[RetrievedCandidate]:
        raise NotImplementedError
