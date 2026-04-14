from __future__ import annotations

from app.config.settings import AppConfig
from app.explanation.templates import build_explanation
from app.rerank.base import NoOpReranker
from app.retrieval.sparse import SparseRetriever
from app.schemas.assessment import AssessmentResult
from app.schemas.idea import IdeaInput
from app.scoring.rules import score_candidates


class PriorArtAssessmentPipeline:
    def __init__(self, config: AppConfig):
        self.config = config
        self.retriever = SparseRetriever(config.paths.sparse_index_path, config.retrieval)
        self.reranker = NoOpReranker()

    def assess(self, idea: IdeaInput) -> AssessmentResult:
        retrieved = self.retriever.retrieve(idea)
        reranked = self.reranker.rerank(idea, retrieved)
        risk_score, risk_label, evidence, debug = score_candidates(reranked, self.config.scoring)
        explanation = build_explanation(risk_label, risk_score, evidence)
        return AssessmentResult(
            idea_id=idea.idea_id,
            risk_label=risk_label,
            risk_score=risk_score,
            evidence=evidence,
            explanation=explanation,
            debug=debug,
        )
