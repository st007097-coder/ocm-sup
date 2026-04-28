"""
Sentiment Heuristic - determines if a fact represents positive/active or negative/stable intent.
Used to flag potential contradictions for LLM judgment.
"""

from typing import Literal

# Markers for positive/active sentiment (快節奏型)
POSITIVE_MARKERS = [
    "快", "active", "dynamic", "新", "變", "high-speed", "fast",
    "積極", "敏捷", "靈活", "創新", "變化", "節奏快", "高效率"
]

# Markers for negative/stable sentiment (穩定型)
NEGATIVE_MARKERS = [
    "慢", "stable", "steady", "穩", "守", "固定", "slow", "傳統",
    "保守", "穩定", "一貫", "按步", "固定流程", "規則為本", "slow-paced"
]

# Neutral indicators (neither positive nor negative)
NEUTRAL_MARKERS = [
    "普通", "一般", "正常", "neutral", "中立的"
]


def get_sentiment_sign(text: str) -> Literal[1, -1, 0]:
    """
    Determine sentiment sign of a fact.

    Returns:
        1  = positive/active (prefers fast-paced, dynamic)
        -1 = negative/stable (prefers slow-paced, stable)
        0  = neutral/unknown
    """
    text_lower = text.lower()

    pos_count = sum(1 for marker in POSITIVE_MARKERS if marker in text_lower)
    neg_count = sum(1 for marker in NEGATIVE_MARKERS if marker in text_lower)

    if pos_count > neg_count:
        return 1
    elif neg_count > pos_count:
        return -1
    else:
        return 0


def get_sentiment_label(text: str) -> str:
    """Human-readable sentiment label."""
    sign = get_sentiment_sign(text)
    if sign == 1:
        return "positive/active"
    elif sign == -1:
        return "negative/stable"
    else:
        return "neutral"


def is_opposite_sign(sign_a: int, sign_b: int) -> bool:
    """Check if two sentiment signs are opposite (potential contradiction)."""
    return sign_a != 0 and sign_b != 0 and sign_a != sign_b


def compute_contradiction_hints(text_a: str, text_b: str) -> dict:
    """
    Compute heuristic hints for potential contradiction between two facts.

    Returns dict with:
        - similarity: cosine similarity (placeholder, computed at higher level)
        - opposite_sign: bool
        - sign_a, sign_b: sentiment signs
        - suggests_contradiction: bool
    """
    sign_a = get_sentiment_sign(text_a)
    sign_b = get_sentiment_sign(text_b)

    return {
        "sign_a": sign_a,
        "sign_b": sign_b,
        "opposite_sign": is_opposite_sign(sign_a, sign_b),
        "suggests_contradiction": is_opposite_sign(sign_a, sign_b)
    }