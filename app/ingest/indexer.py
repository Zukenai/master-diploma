from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from app.schemas.paper import PaperRecord
from app.utils.text import term_frequency, tokenize


def _paper_text(paper: PaperRecord) -> str:
    segments = [paper.title, paper.abstract, *paper.keywords, *paper.claims]
    return " ".join(segments)


def _document_frequency(tokenized_documents: list[list[str]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for tokens in tokenized_documents:
        counts.update(set(tokens))
    return dict(counts)


def build_sparse_index(raw_path: Path, processed_path: Path, index_path: Path) -> dict[str, object]:
    records_data = json.loads(raw_path.read_text(encoding="utf-8"))
    papers = [PaperRecord.model_validate(item) for item in records_data]

    processed_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    tokenized_documents = [tokenize(_paper_text(paper)) for paper in papers]
    doc_frequency = _document_frequency(tokenized_documents)
    total_docs = len(tokenized_documents) or 1

    processed_payload = [paper.model_dump(mode="json") for paper in papers]
    processed_path.write_text(
        json.dumps(processed_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    documents: list[dict[str, object]] = []
    for paper, tokens in zip(papers, tokenized_documents, strict=True):
        tf = term_frequency(tokens)
        tfidf = {
            token: round(tf_value * (math.log((1 + total_docs) / (1 + doc_frequency[token])) + 1), 6)
            for token, tf_value in tf.items()
        }
        title_tokens = tokenize(paper.title)
        keyword_tokens = [token for keyword in paper.keywords for token in tokenize(keyword)]
        documents.append(
            {
                "paper": paper.model_dump(mode="json"),
                "tfidf": tfidf,
                "tokens": tokens,
                "title_tokens": title_tokens,
                "keyword_tokens": keyword_tokens,
            }
        )

    index_payload = {
        "document_count": len(documents),
        "documents": documents,
        "document_frequency": doc_frequency,
    }
    index_path.write_text(
        json.dumps(index_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return index_payload
