from __future__ import annotations

import re
from collections import Counter
from typing import Any


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "with", "you", "your",
    "ai", "la", "là", "va", "và", "ve", "về", "cho", "cac", "các", "cua",
    "của", "mot", "một", "nhung", "những", "trong", "tren", "trên",
}


def extract_keywords(text: str, max_keywords: int = 8, min_length: int = 3) -> dict[str, Any]:
    """Extract simple keyword frequency from user-provided text."""
    text = (text or "").strip()
    max_keywords = max(1, min(int(max_keywords or 8), 25))
    min_length = max(1, int(min_length or 3))

    if not text:
        return {
            "tool": "extract_keywords",
            "error": "missing_text",
            "message": "Provide non-empty text to extract keywords.",
            "keywords": [],
            "keyword_count": 0,
        }

    tokens = [
        token.lower()
        for token in re.findall(r"[\wÀ-ỹ]+", text, flags=re.UNICODE)
        if len(token) >= min_length and token.lower() not in STOPWORDS
    ]
    counts = Counter(tokens)
    keywords = [
        {"keyword": keyword, "count": count}
        for keyword, count in counts.most_common(max_keywords)
    ]

    return {
        "tool": "extract_keywords",
        "error": None,
        "message": None,
        "keywords": keywords,
        "keyword_count": len(keywords),
        "token_count": len(tokens),
    }
