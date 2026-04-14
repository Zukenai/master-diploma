from __future__ import annotations

from pydantic import BaseModel, Field


class PaperRecord(BaseModel):
    paper_id: str
    title: str
    abstract: str
    keywords: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    year: int
    venue: str


class RetrievedCandidate(BaseModel):
    paper: PaperRecord
    score: float
    source_retrievers: list[str] = Field(default_factory=list)
    sparse_score: float | None = None
    dense_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None
    matched_terms: list[str] = Field(default_factory=list)
    title_overlap_terms: list[str] = Field(default_factory=list)
    keyword_overlap_terms: list[str] = Field(default_factory=list)
    claim_overlap_terms: list[str] = Field(default_factory=list)
    debug_signals: dict[str, float | int | str | list[str]] = Field(default_factory=dict)
