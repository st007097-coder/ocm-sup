"""
OCM Sup Continuity Layer
========================

Extension to OCM Sup that adds /new carryover and structured follow-up.

Architecture:
- State Router: Route messages into casual/staged/tracked
- Carryover: /new session continuity reattachment
- Hook Lifecycle: due/render/complete for follow-ups
- Settings Manager: sleep/wake/proactive settings
- Causal Memory: Structured traces for staged/tracked items
- Frontstage Guard: Prevent internal logic from leaking
- OCM Graph Integration: Store continuity in wiki entities
- Daily Memory Traces: Auditable trail for continuity events

Version: 1.0.0 (Phase 1 + Phase 2)
"""

__version__ = "1.0.0"
__phase__ = "Phase 1 + Phase 2 Complete"

from .state_router import StateRouter, MessageClassification, RoutingType, EventType
from .carryover import CarryoverManager, Turn, PendingTopic
from .continuity_state import ContinuityState
from .hook_lifecycle import HookLifecycle, HookStatus, ClosureReason, Hook
from .frontstage_guard import FrontstageGuard
from .ocm_graph_integration import OCMGraphIntegration
from .daily_memory_trace import DailyMemoryTrace

__all__ = [
    # Core
    "ContinuityState",
    
    # State Router
    "StateRouter",
    "MessageClassification",
    "RoutingType",
    "EventType",
    
    # Carryover
    "CarryoverManager",
    "Turn",
    "PendingTopic",
    
    # Hook Lifecycle
    "HookLifecycle",
    "HookStatus",
    "ClosureReason",
    "Hook",
    
    # Frontstage
    "FrontstageGuard",
    
    # OCM Graph
    "OCMGraphIntegration",
    
    # Daily Memory
    "DailyMemoryTrace",
]
