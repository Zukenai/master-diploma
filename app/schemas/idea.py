from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class IdeaInput(BaseModel):
    idea_id: str = Field(..., min_length=3)
    title: str = Field(..., min_length=10)
    abstract: str = Field(..., min_length=30)
    keywords: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)

    @field_validator("keywords", "claims")
    @classmethod
    def strip_values(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]
