"""
P3 Reliability Layer - OCM Sup v2.4
Semantic Contradiction Engine + Transaction System + Pruning Policy + Memory Usage Tracker
"""

from . import contradiction
from . import transaction
from . import pruning
from . import usage
from .api import p3_routes

__version__ = "2.4"
__all__ = [
    "contradiction",
    "transaction",
    "pruning",
    "usage",
    "p3_routes"
]