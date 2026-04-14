from __future__ import annotations

from app.schemas.idea import IdeaInput


def build_query_text(idea: IdeaInput) -> str:
    parts = [idea.title, idea.abstract, *idea.keywords, *idea.claims]
    return " ".join(part for part in parts if part)
