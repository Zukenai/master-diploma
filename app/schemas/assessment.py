from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    paper_id: str
    title: str
    score: float
    source_retrievers: list[str] = Field(default_factory=list)
    sparse_score: float | None = None
    dense_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None
    overlap_signals: dict[str, float | int | list[str]]
    rationale: str


class AssessmentResult(BaseModel):
    idea_id: str
    risk_label: Literal["high prior-art risk", "medium prior-art risk", "low prior-art risk"]
    risk_score: float = Field(..., ge=0.0, le=1.0)
    evidence: list[EvidenceItem]
    explanation: str
    debug: dict[str, float | int | str | list[str]]
