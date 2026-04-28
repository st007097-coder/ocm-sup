"""
P3 Reliability Layer - OCM Sup v2.4

⚠️ DEPRECATED - This module is deprecated as of v2.6.

Please use `memory_reliability_layer` instead.

Migration:
  - p3_reliability.transaction.TxManager → memory_reliability_layer.TransactionManager
  - p3_reliability.contradiction.Detector → memory_reliability_layer.ContradictionEngine
  - p3_reliability.usage.Tracker → memory_reliability_layer.UsageTracker
  - p3_reliability.pruning.Policy → memory_reliability_layer.AdaptivePruning

This module will be removed in a future version.
"""

from . import contradiction
from . import transaction
from . import pruning
from . import usage

__version__ = "2.4-deprecated"
__all__ = [
    "contradiction",
    "transaction",
    "pruning",
    "usage"
]