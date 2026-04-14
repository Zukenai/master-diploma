from __future__ import annotations

from app.config.settings import AppConfig
from app.explanation.templates import build_explanation
from app.rerank.base import NoOpReranker, OverlapReranker
from app.retrieval.factory import build_retriever
from app.schemas.assessment import AssessmentResult
from app.schemas.idea import IdeaInput
from app.scoring.rules import score_candidates


class PriorArtAssessmentPipeline:
    def __init__(self, config: AppConfig, retrieval_strategy: str | None = None):
        self.config = config
        self.retriever = build_retriever(config, retrieval_strategy)
        self.reranker = (
            OverlapReranker(config.reranker)
            if config.reranker.strategy == "overlap"
            else NoOpReranker()
        )

    def assess(self, idea: IdeaInput) -> AssessmentResult:
        retrieved = self.retriever.retrieve(idea)
        reranked = self.reranker.rerank(idea, retrieved)
        risk_score, risk_label, evidence, debug = score_candidates(reranked, self.config.scoring)
        explanation = build_explanation(risk_label, risk_score, evidence)
        debug["retrieval_strategy"] = getattr(self.retriever, "name", "unknown")
        debug["reranker_strategy"] = self.config.reranker.strategy
        return AssessmentResult(
            idea_id=idea.idea_id,
            risk_label=risk_label,
            risk_score=risk_score,
            evidence=evidence,
            explanation=explanation,
            debug=debug,
        )
