"""
Health Metrics
OCM Sup v2.6

Compute and report memory system health indicators.
Based on user's health_metrics.py approach with enhancements.

Usage:
    metrics = HealthMetrics()
    report = metrics.compute()
    metrics.save_report(report)
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from . import config


class HealthReport:
    """Health report with multiple indicators."""
    
    def __init__(self):
        self.duplicate_rate = 0.0
        self.contradiction_rate = 0.0
        self.unused_rate = 0.0
        self.freshness_score = 1.0
        self.health_score = 0.0
        self.total_facts = 0
        self.used_facts = 0
        self.contradictions_found = 0
        self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    
    def to_dict(self) -> dict:
        return {
            "duplicate_rate": self.duplicate_rate,
            "contradiction_rate": self.contradiction_rate,
            "unused_rate": self.unused_rate,
            "freshness_score": self.freshness_score,
            "health_score": self.health_score,
            "total_facts": self.total_facts,
            "used_facts": self.used_facts,
            "contradictions_found": self.contradictions_found,
            "timestamp": self.timestamp
        }


class HealthMetrics:
    """
    Compute health metrics for memory system.
    
    Metrics computed:
    - duplicate_rate: Rate of duplicate facts
    - contradiction_rate: Rate of contradicting facts
    - unused_rate: Rate of facts never used in output
    - freshness_score: Average age of facts
    - overall health_score: Weighted average
    """
    
    def __init__(self, usage_tracker=None, contradiction_engine=None):
        self.usage_tracker = usage_tracker
        self.contradiction_engine = contradiction_engine
        config.HEALTH_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_facts(self) -> List[dict]:
        """Load all facts from structured storage."""
        facts = []
        if config.STORAGE_DIR.exists():
            for fpath in config.STORAGE_DIR.glob("*.json"):
                try:
                    with open(fpath) as f:
                        data = json.load(f)
                        data["entity_id"] = data.get("entity_id", fpath.stem)
                        facts.append(data)
                except:
                    pass
        return facts
    
    def _compute_duplicate_rate(self, facts: List[dict]) -> float:
        """Compute rate of duplicate facts."""
        if len(facts) < 2:
            return 0.0
        
        subjects = [f.get("subject", "") for f in facts]
        unique_subjects = set(subjects)
        
        # Simple duplicate detection: same subject
        duplicates = len(subjects) - len(unique_subjects)
        return duplicates / len(facts)
    
    def _compute_contradiction_rate(self, facts: List[dict]) -> float:
        """Compute rate of contradicting facts."""
        if not self.contradiction_engine or len(facts) < 2:
            return 0.0
        
        try:
            results = self.contradiction_engine.run_full_scan()
            contradictions_found = len(results)
            return contradictions_found / len(facts) if facts else 0.0
        except Exception as e:
            print(f"[HEALTH] Contradiction check failed: {e}")
            return 0.0
    
    def _compute_unused_rate(self, facts: List[dict], usage_data: dict) -> float:
        """Compute rate of facts never used in output."""
        if not self.usage_tracker or len(facts) < 1:
            return 0.0
        
        used_count = 0
        for fact in facts:
            fact_id = fact.get("entity_id", "")
            if self.usage_tracker.is_fact_used(fact_id):
                used_count += 1
        
        return 1 - (used_count / len(facts)) if facts else 0.0
    
    def _compute_freshness_score(self, facts: List[dict]) -> float:
        """
        Compute freshness score (0.0 - 1.0).
        Based on average age of facts.
        """
        if len(facts) < 1:
            return 1.0
        
        now = time.time()
        ages = []
        
        for fact in facts:
            timestamp = fact.get("created_at") or fact.get("timestamp", now)
            # Handle string timestamps
            if isinstance(timestamp, str):
                try:
                    from datetime import datetime
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
                except:
                    timestamp = now
            age_days = (now - float(timestamp)) / 86400
            ages.append(age_days)
        
        avg_age = sum(ages) / len(ages)
        
        # Score: 1.0 for very new, 0.0 for very old (>30 days)
        freshness = max(0.0, 1.0 - (avg_age / 30.0))
        
        return round(freshness, 4)
    
    def compute(self) -> HealthReport:
        """
        Compute all health metrics.
        
        Returns:
            HealthReport with all indicators
        """
        report = HealthReport()
        
        # Load facts
        facts = self._load_facts()
        report.total_facts = len(facts)
        
        # Load usage data if tracker available
        usage_data = {}
        if self.usage_tracker:
            summary = self.usage_tracker.get_summary()
            report.used_facts = summary.get("used_in_output", 0)
            # Build usage data dict for pruning
            usage_data = self.usage_tracker._data
        
        # Compute metrics
        report.duplicate_rate = self._compute_duplicate_rate(facts)
        report.contradiction_rate = self._compute_contradiction_rate(facts)
        report.unused_rate = self._compute_unused_rate(facts, usage_data)
        report.freshness_score = self._compute_freshness_score(facts)
        
        # Compute overall health score (weighted average)
        # Weights: contradiction 30%, duplicates 20%, unused 20%, freshness 30%
        report.health_score = (
            (1 - report.contradiction_rate) * 0.30 +
            (1 - report.duplicate_rate) * 0.20 +
            (1 - report.unused_rate) * 0.20 +
            report.freshness_score * 0.30
        )
        report.health_score = round(report.health_score, 4)
        
        return report
    
    def save_report(self, report: HealthReport, path: Path = None):
        """
        Save health report to disk.
        
        Args:
            report: HealthReport to save
            path: Optional custom path (default: config.HEALTH_REPORT_PATH)
        """
        if path is None:
            path = config.HEALTH_REPORT_PATH
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    
    def get_weekly_report(self) -> Optional[dict]:
        """Load most recent weekly report."""
        path = config.HEALTH_REPORT_PATH
        
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except:
                pass
        
        return None
    
    def print_report(self, report: HealthReport):
        """Print health report to console."""
        print("=== Memory Health Report ===")
        print(f"Total facts: {report.total_facts}")
        print(f"Health score: {report.health_score:.2%}")
        print(f"  - Contradiction rate: {report.contradiction_rate:.2%}")
        print(f"  - Duplicate rate: {report.duplicate_rate:.2%}")
        print(f"  - Unused rate: {report.unused_rate:.2%}")
        print(f"  - Freshness score: {report.freshness_score:.2%}")
        print(f"  - Used in output: {report.used_facts}")
        print(f"Generated: {report.timestamp}")
