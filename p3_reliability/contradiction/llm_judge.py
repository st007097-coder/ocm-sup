"""
LLM Judge - lightweight LLM call to judge if two facts represent a conflict.
Uses Ollama (localhost:11434) for actual LLM inference.
"""

import requests
import json
from typing import Optional

JUDGE_PROMPT = """You are a concise conflict detector. Judge if two facts represent conflicting preferences or beliefs.

Fact A: {fact_a}
Fact B: {fact_b}

Respond with exactly one line:
- If CONFLICT: "CONFLICT|0.85|one sentence explanation"
  where 0.85 is your confidence score (0.0-1.0)
- If NO_CONFLICT: "NO_CONFLICT"

Examples:
CONFLICT|0.85|Both express opposite attitudes toward change.
NO_CONFLICT"""


class LLMJudge:
    """
    Lightweight LLM wrapper for contradiction judgment.

    Connects to local Ollama instance (http://localhost:11434).
    Falls back to heuristic-only mode if Ollama unavailable.
    """

    def __init__(
        self,
        model: str = "minimax/m2",
        base_url: str = "http://localhost:11434"
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    @property
    def is_available(self) -> bool:
        """Returns True if LLM is currently reachable."""
        return self._available

    def judge(self, fact_a: str, fact_b: str, use_heuristic_fallback: bool = True) -> dict:
        """
        Judge if two facts conflict.

        Args:
            fact_a: First fact text
            fact_b: Second fact text
            use_heuristic_fallback: If True, use heuristic when LLM unavailable

        Returns:
            {
                "contradiction": bool,
                "confidence": float (0.0-1.0),
                "explanation": str,
                "source": "llm" or "heuristic"
            }
        """
        prompt = JUDGE_PROMPT.format(fact_a=fact_a, fact_b=fact_b)

        if self._available:
            try:
                result = self._call_ollama(prompt)
                result["source"] = "llm"
                return result
            except Exception as e:
                # LLM call failed - fall through to heuristic
                pass

        # Fallback to heuristic-only mode
        if use_heuristic_fallback:
            return self._heuristic_judge(fact_a, fact_b)

        return {
            "contradiction": False,
            "confidence": 0.0,
            "explanation": "LLM unavailable",
            "source": "none"
        }

    def _call_ollama(self, prompt: str) -> dict:
        """
        Call Ollama chat completion endpoint.

        Args:
            prompt: The formatted prompt

        Returns:
            Parsed response dict
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temp for deterministic output
                "num_predict": 50     # Short response - just the judgment line
            }
        }

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama returned {response.status_code}: {response.text}")

        data = response.json()
        content = data.get("message", {}).get("content", "")
        return self._parse_response(content)

    def _parse_response(self, response: str) -> dict:
        """Parse LLM response into structured format."""
        response = response.strip()

        if response.startswith("CONFLICT|"):
            parts = response.split("|", 2)
            if len(parts) >= 3:
                try:
                    confidence = float(parts[1])
                    explanation = parts[2]
                    return {
                        "contradiction": True,
                        "confidence": confidence,
                        "explanation": explanation
                    }
                except ValueError:
                    pass

        return {
            "contradiction": False,
            "confidence": 0.0,
            "explanation": ""
        }

    def _heuristic_judge(self, fact_a: str, fact_b: str) -> dict:
        """
        Fallback heuristic judgment when LLM is unavailable.

        Uses sentiment analysis to detect obvious contradictions.
        This is a best-effort fallback, not a replacement for LLM.
        """
        from .sentiment import get_sentiment_sign, is_opposite_sign

        sign_a = get_sentiment_sign(fact_a)
        sign_b = get_sentiment_sign(fact_b)

        # Only flag as contradiction if signs are clearly opposite
        if is_opposite_sign(sign_a, sign_b):
            return {
                "contradiction": True,
                "confidence": 0.5,  # Lower confidence for heuristic-only
                "explanation": f"Heuristic: opposite sentiment signs ({sign_a} vs {sign_b})",
                "source": "heuristic"
            }

        return {
            "contradiction": False,
            "confidence": 0.0,
            "explanation": "No obvious heuristic contradiction",
            "source": "heuristic"
        }

    def batch_judge(self, pairs: list[tuple[str, str]]) -> list[dict]:
        """
        Judge multiple fact pairs in batch.

        Args:
            pairs: list of (fact_a, fact_b) tuples

        Returns:
            list of judgment dicts (same order as input)
        """
        results = []
        for fact_a, fact_b in pairs:
            results.append(self.judge(fact_a, fact_b))
        return results

    def get_status(self) -> dict:
        """Get LLM judge status."""
        return {
            "model": self.model,
            "available": self._available,
            "base_url": self.base_url
        }


def judge_pair(fact_a: str, fact_b: str) -> dict:
    """
    Convenience function for single judgment.
    """
    judge = LLMJudge()
    return judge.judge(fact_a, fact_b)