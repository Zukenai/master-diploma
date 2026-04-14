from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.idea import IdeaInput
from app.schemas.paper import RetrievedCandidate


class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, idea: IdeaInput) -> list[RetrievedCandidate]:
        raise NotImplementedError
