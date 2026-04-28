"""
Usage Tracker
OCM Sup v2.6

Simple count-based usage tracking for memory facts.
Based on user's simple approach.

Usage:
    tracker = UsageTracker()
    tracker.on_retrieve(fact_id, context="search query")
    tracker.on_output(fact_id)
    stats = tracker.get_stats(fact_id)
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from . import config


class UsageStats:
    """Usage statistics for a fact."""
    
    def __init__(self, retrieve_count: int = 0, used_in_output: bool = False, 
                 last_retrieved: str = None, last_used: str = None):
        self.retrieve_count = retrieve_count
        self.used_in_output = used_in_output
        self.last_retrieved = last_retrieved
        self.last_used = last_used
    
    def to_dict(self) -> dict:
        return {
            "retrieve_count": self.retrieve_count,
            "used_in_output": self.used_in_output,
            "last_retrieved": self.last_retrieved,
            "last_used": self.last_used
        }


class UsageTracker:
    """
    Simple count-based usage tracker.
    
    Tracks:
    - retrieve_count: Number of times a fact was retrieved
    - used_in_output: Whether fact was used in agent output
    - last_retrieved: Timestamp of last retrieval
    - last_used: Timestamp of last output usage
    """
    
    def __init__(self, usage_file: Path = None):
        self.usage_file = usage_file or config.USAGE_FILE
        self._data: Dict[str, dict] = {}
        self._load()
    
    def _load(self):
        """Load usage data from disk."""
        if self.usage_file.exists():
            try:
                with open(self.usage_file) as f:
                    self._data = json.load(f)
            except json.JSONDecodeError:
                self._data = {}
        else:
            self._data = {}
    
    def _save(self):
        """Save usage data to disk."""
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_file, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
    
    def _ensure_fact(self, fact_id: str):
        """Ensure fact exists in tracking data."""
        if fact_id not in self._data:
            self._data[fact_id] = {
                "retrieve_count": 0,
                "used_in_output": False,
                "last_retrieved": None,
                "last_used": None
            }
    
    def _now(self) -> str:
        """Get current timestamp."""
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    
    def on_retrieve(self, fact_id: str, context: str = ""):
        """
        Record that a fact was retrieved.
        
        Args:
            fact_id: ID of the retrieved fact
            context: Optional context (e.g., search query)
        """
        self._ensure_fact(fact_id)
        self._data[fact_id]["retrieve_count"] += 1
        self._data[fact_id]["last_retrieved"] = self._now()
        self._save()
    
    def on_output(self, fact_id: str):
        """
        Record that a fact was used in agent output.
        
        Args:
            fact_id: ID of the fact used in output
        """
        self._ensure_fact(fact_id)
        self._data[fact_id]["used_in_output"] = True
        self._data[fact_id]["last_used"] = self._now()
        self._save()
    
    def on_agent_decision(self, pattern: str, facts_used: List[str]):
        """
        Record agent decision influenced by memory.
        
        Args:
            pattern: Context pattern (e.g., "user debugging system")
            facts_used: List of fact IDs that influenced decision
        """
        for fact_id in facts_used:
            self.on_retrieve(fact_id, context=pattern)
        self._save()
    
    def get_stats(self, fact_id: str) -> Optional[dict]:
        """
        Get usage statistics for a fact.
        
        Returns None if fact not tracked.
        """
        if fact_id not in self._data:
            return None
        
        data = self._data[fact_id]
        retrieve_count = data.get("retrieve_count", 0)
        used_in_output = data.get("used_in_output", False)
        
        return {
            "retrieve_count": retrieve_count,
            "used_in_output": used_in_output,
            "last_retrieved": data.get("last_retrieved"),
            "last_used": data.get("last_used"),
            "usage_ratio": (
                1.0 if used_in_output else 0.0
            ) / retrieve_count if retrieve_count > 0 else 0
        }
    
    def get_ignored_facts(self, min_retrieves: int = 5, usage_threshold: float = 0.1) -> List[str]:
        """
        Get facts that are frequently retrieved but never used.
        
        Args:
            min_retrieves: Minimum retrieval count to consider
            usage_threshold: Max usage ratio to be considered "ignored"
            
        Returns:
            List of ignored fact IDs
        """
        ignored = []
        
        for fact_id, data in self._data.items():
            retrieve_count = data.get("retrieve_count", 0)
            
            if retrieve_count >= min_retrieves:
                # Calculate usage ratio
                used = data.get("used_in_output", False)
                ratio = (1.0 if used else 0.0) / retrieve_count
                
                if ratio < usage_threshold:
                    ignored.append(fact_id)
        
        return ignored
    
    def is_fact_used(self, fact_id: str) -> bool:
        """Check if a fact has ever been used in output."""
        return self._data.get(fact_id, {}).get("used_in_output", False)
    
    def get_utilization_rate(self) -> float:
        """
        Calculate overall memory utilization rate.
        
        Returns ratio of facts used in output vs total retrieved.
        """
        total_retrieves = sum(d.get("retrieve_count", 0) for d in self._data.values())
        total_used = sum(1 for d in self._data.values() if d.get("used_in_output", False))
        
        if total_retrieves == 0:
            return 0.0
        
        return total_used / len(self._data)
    
    def get_summary(self) -> dict:
        """Get summary statistics."""
        total_facts = len(self._data)
        total_retrieves = sum(d.get("retrieve_count", 0) for d in self._data.values())
        total_used = sum(1 for d in self._data.values() if d.get("used_in_output", False))
        ignored = self.get_ignored_facts(min_retrieves=3)
        
        return {
            "total_tracked_facts": total_facts,
            "total_retrieves": total_retrieves,
            "used_in_output": total_used,
            "ignored_count": len(ignored),
            "ignored_facts": ignored[:10]  # Top 10
        }
