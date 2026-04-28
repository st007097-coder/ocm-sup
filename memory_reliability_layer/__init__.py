"""
Memory Reliability Layer
OCM Sup v2.6

A lightweight, production-ready memory reliability layer.
Based on user's suggestions with P3 reliability concepts.

Core modules:
- tx_manager: Transaction management with rollback
- contradiction: Semantic contradiction detection
- usage_tracker: Simple usage tracking
- adaptive_pruning: Score-based pruning with archiving
- health_metrics: Health indicator computation
- config: Configuration

Usage:
    from memory_reliability_layer import (
        TransactionManager,
        ContradictionEngine,
        UsageTracker,
        AdaptivePruning,
        HealthMetrics
    )
"""

from .tx_manager import TransactionManager
from .contradiction import ContradictionEngine, ContradictionResult
from .usage_tracker import UsageTracker, UsageStats
from .adaptive_pruning import AdaptivePruning, PruningResult
from .health_metrics import HealthMetrics, HealthReport
from .idempotency_guard import is_duplicate, make_id
from . import config

__all__ = [
    "TransactionManager",
    "ContradictionEngine",
    "ContradictionResult",
    "UsageTracker",
    "UsageStats",
    "AdaptivePruning",
    "PruningResult",
    "HealthMetrics",
    "HealthReport",
    "is_duplicate",
    "make_id",
    "config"
]
