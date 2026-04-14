from __future__ import annotations

from app.retrieval.query import build_query_text
from app.schemas.idea import IdeaInput
from app.schemas.paper import PaperRecord
from app.utils.text import compute_overlap_terms, tokenize


def build_overlap_metadata(
    idea: IdeaInput,
    paper: PaperRecord,
) -> dict[str, list[str] | int]:
    query_tokens = tokenize(build_query_text(idea))
    title_tokens = tokenize(idea.title)
    keyword_tokens = [token for keyword in idea.keywords for token in tokenize(keyword)]
    paper_tokens = tokenize(" ".join([paper.title, paper.abstract, *paper.keywords, *paper.claims]))
    paper_title_tokens = tokenize(paper.title)
    paper_keyword_tokens = [token for keyword in paper.keywords for token in tokenize(keyword)]

    matched_terms = compute_overlap_terms(query_tokens, paper_tokens)[:10]
    title_overlap_terms = compute_overlap_terms(title_tokens, paper_title_tokens)[:8]
    keyword_overlap_terms = compute_overlap_terms(keyword_tokens, paper_keyword_tokens)[:8]
    return {
        "matched_terms": matched_terms,
        "title_overlap_terms": title_overlap_terms,
        "keyword_overlap_terms": keyword_overlap_terms,
        "matched_term_count": len(matched_terms),
        "title_overlap_count": len(title_overlap_terms),
        "keyword_overlap_count": len(keyword_overlap_terms),
    }
