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
    claim_tokens = [token for claim in idea.claims for token in tokenize(claim)]
    paper_tokens = tokenize(" ".join([paper.title, paper.abstract, *paper.keywords, *paper.claims]))
    paper_title_tokens = tokenize(paper.title)
    paper_keyword_tokens = [token for keyword in paper.keywords for token in tokenize(keyword)]
    paper_claim_tokens = [token for claim in paper.claims for token in tokenize(claim)]

    matched_terms = compute_overlap_terms(query_tokens, paper_tokens)[:10]
    title_overlap_terms = compute_overlap_terms(title_tokens, paper_title_tokens)[:8]
    keyword_overlap_terms = compute_overlap_terms(keyword_tokens, paper_keyword_tokens)[:8]
    claim_overlap_terms = compute_overlap_terms(claim_tokens, paper_claim_tokens)[:8]
    facet_overlap_count = sum(
        1
        for overlap_terms in [title_overlap_terms, keyword_overlap_terms, claim_overlap_terms]
        if overlap_terms
    )
    return {
        "matched_terms": matched_terms,
        "title_overlap_terms": title_overlap_terms,
        "keyword_overlap_terms": keyword_overlap_terms,
        "claim_overlap_terms": claim_overlap_terms,
        "matched_term_count": len(matched_terms),
        "title_overlap_count": len(title_overlap_terms),
        "keyword_overlap_count": len(keyword_overlap_terms),
        "claim_overlap_count": len(claim_overlap_terms),
        "facet_overlap_count": facet_overlap_count,
    }
