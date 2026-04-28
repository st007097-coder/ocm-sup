"""
Tests for P3 Contradiction Engine.
"""

import pytest
import sys
from pathlib import Path

# Add p3_reliability to path
sys.path.insert(0, str(Path(__file__).parent.parent / "p3_reliability"))

from contradiction.sentiment import get_sentiment_sign, is_opposite_sign
from contradiction.embedding_store import EmbeddingStore
from contradiction.llm_judge import LLMJudge


class TestSentiment:
    def test_positive_sign(self):
        assert get_sentiment_sign("我鍾意快節奏工作") == 1

    def test_negative_sign(self):
        assert get_sentiment_sign("我偏好穩定環境") == -1

    def test_neutral_sign(self):
        assert get_sentiment_sign("今日天氣普通") == 0

    def test_opposite_sign(self):
        assert is_opposite_sign(1, -1) == True
        assert is_opposite_sign(1, 1) == False
        assert is_opposite_sign(0, -1) == False


class TestEmbeddingStore:
    def test_store_and_retrieve(self):
        store = EmbeddingStore()
        test_id = "test_fact_001"
        test_emb = [0.1] * 1536

        store.store(test_id, test_emb, {"source": "test"})
        assert store.exists(test_id)

        retrieved = store.get(test_id)
        assert retrieved is not None
        assert len(retrieved) == 1536

    def test_delete(self):
        store = EmbeddingStore()
        test_id = "test_fact_002"
        test_emb = [0.2] * 1536

        store.store(test_id, test_emb)
        assert store.exists(test_id)

        store.delete(test_id)
        assert not store.exists(test_id)


class TestLLMJudge:
    def test_no_conflict(self):
        judge = LLMJudge()
        result = judge.judge(
            "I prefer fast-paced work",
            "I enjoy dynamic environments"
        )
        # Both positive - should not conflict
        assert result["contradiction"] == False

    def test_parse_conflict_response(self):
        judge = LLMJudge()
        # Test parsing CONFLICT response
        parsed = judge._parse_response("CONFLICT|0.85|Opposing attitudes toward change.")
        assert parsed["contradiction"] == True
        assert parsed["confidence"] == 0.85

    def test_parse_no_conflict_response(self):
        judge = LLMJudge()
        parsed = judge._parse_response("NO_CONFLICT")
        assert parsed["contradiction"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])