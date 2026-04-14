from __future__ import annotations

import math
import re
from collections import Counter


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def compute_overlap_terms(left: list[str], right: list[str]) -> list[str]:
    return sorted(set(left).intersection(right))


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    common = set(left).intersection(right)
    dot = sum(left[token] * right[token] for token in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def term_frequency(tokens: list[str]) -> dict[str, float]:
    counts = Counter(tokens)
    length = len(tokens) or 1
    return {token: count / length for token, count in counts.items()}
