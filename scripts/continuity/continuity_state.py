"""
Continuity State Manager
========================

Manages the overall continuity state for OCM Sup.
Integrates with:
- State Router (message classification)
- Carryover Manager (/new carryover)
- OCM Sup Knowledge Graph (entity storage)

This is the main entry point for the continuity layer.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from continuity.state_router import StateRouter, RoutingType, EventType, MessageClassification
from continuity.carryover import CarryoverManager


class ContinuityState:
    """
    Main state manager for OCM Sup continuity layer.
    
    This is the facade that combines:
    - StateRouter for message classification
    - CarryoverManager for /new carryover
    - Integration with OCM Sup Knowledge Graph
    
    Usage:
        state = ContinuityState(wiki_path="/path/to/wiki")
        
        # Classify and handle incoming message
        result = state.handle_message("幫我記住...")
        
        # Get context for reply generation
        context = state.build_runtime_context(is_new_session=False)
        
        # Get carryover for /new session
        carryover = state.get_carryover_context(is_new_session=True)
    """
    
    def __init__(
        self,
        wiki_path: str = "/home/jacky/.openclaw/workspace/wiki",
        state_dir: str = "/home/jacky/.openclaw/workspace/OCM-Sup/scripts/continuity",
        ocm_sup_path: str = "/home/jacky/.openclaw/workspace/OCM-Sup"
    ):
        self.wiki_path = Path(wiki_path)
        self.state_dir = Path(state_dir)
        self.ocm_sup_path = Path(ocm_sup_path)
        
        # Ensure directories exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.router = StateRouter(
            wiki_path=str(self.wiki_path),
            state_dir=str(self.state_dir)
        )
        self.carryover = CarryoverManager(
            state_dir=str(self.state_dir)
        )
        
        # Load settings
        self.settings = self._load_settings()
        
        # Track session
        self._is_new_session = False
        self._session_turns = []
    
    def _load_settings(self) -> Dict:
        """Load settings from file"""
        settings_path = self.state_dir / "settings.json"
        if settings_path.exists():
            try:
                return json.loads(settings_path.read_text())
            except:
                pass
        
        # Default settings
        return self._default_settings()
    
    def _default_settings(self) -> Dict:
        """Default settings for the continuity layer"""
        return {
            "version": "1.0.0",
            "updated_at": datetime.now().isoformat(),
            "routine_schedule": {
                "timezone": "Asia/Hong_Kong",
                "sleep_time": "00:00",
                "wake_time": "08:30",
                "phases": {
                    "sleep": {
                        "proactive_enabled": False,
                        "wake_seed_enabled": False,
                    },
                    "wake_window": {
                        "proactive_enabled": True,
                        "wake_seed_enabled": True,
                        "interval_hours": 0.5,
                    },
                    "active_day": {
                        "proactive_enabled": True,
                        "wake_seed_enabled": True,
                        "interval_hours": 2,
                    },
                },
            },
            "carryover": {
                "enabled": True,
                "max_turns": 5,
                "top_summary_only": True,
            },
            "proactive_chat": {
                "enabled": False,  # Disable by default for Phase 1
                "interval_hours": 2,
                "quiet_hours": {
                    "start": 23,
                    "end": 8,
                },
                "cooldown_minutes": 30,
                "max_proactive_per_day": 5,
                "allow_when_no_trackable_thread": False,
            },
            "re_engagement": {
                "mode": "wait_for_reply",
                "retry_after_hours": 4,
                "max_unanswered_before_park": 2,
            },
            "causal_memory": {
                "summary_max_facts": 3,
                "include_time_anchor": True,
                "include_state_marker": True,
            },
            "closure": {
                "auto_close_on_user_reply": True,
            },
        }
    
    def handle_message(
        self,
        user_text: str,
        assistant_text: Optional[str] = None,
        context: Optional[Dict] = None,
        is_new_session: bool = False
    ) -> Dict:
        """
        Handle an incoming message.
        
        This is the main entry point for the continuity layer.
        It:
        1. Classifies the message
        2. Updates carryover buffer
        3. Writes staged/tracked items if needed
        4. Returns classification result
        
        Args:
            user_text: The user's message
            assistant_text: Optional assistant reply (for tracking)
            context: Optional additional context
            is_new_session: Whether this is a /new session
            
        Returns:
            Dict with classification result and actions taken
        """
        self._is_new_session = is_new_session
        
        # Track turn
        self._session_turns.append({
            "role": "user",
            "text": user_text,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Classify message
        classification = self.router.classify(user_text, context)
        
        result = {
            "classification": {
                "routing": classification.routing.value,
                "event_type": classification.event_type.value if classification.event_type else None,
                "confidence": classification.confidence,
                "entity_name": classification.entity_name,
                "followup_focus": classification.followup_focus,
            },
            "actions": [],
            "pending_topic": None,
        }
        
        # Handle based on routing type
        if classification.routing == RoutingType.STAGED_MEMORY:
            # Write to staging
            item_id = self.router.write_staged_item(classification)
            result["actions"].append({
                "action": "stage_item",
                "item_id": item_id,
            })
            
            # Set as pending topic for carryover
            self.carryover.set_pending_topic(
                topic_id=item_id,
                entity_name=classification.entity_name,
                event_type=classification.event_type.value if classification.event_type else "parked_topic",
                context_before=classification.context_before,
                event_core=classification.event_core,
                followup_focus=classification.followup_focus,
                causal_memory=classification.causal_memory,
            )
            result["pending_topic"] = self.carryover.get_pending_topic()
        
        elif classification.routing == RoutingType.TRACKED_FOLLOWUP:
            # Write to incidents
            incident_id = self.router.write_tracked_incident(classification)
            result["actions"].append({
                "action": "track_incident",
                "incident_id": incident_id,
            })
            
            # Set as pending topic
            self.carryover.set_pending_topic(
                topic_id=incident_id,
                entity_name=classification.entity_name,
                event_type=classification.event_type.value if classification.event_type else "tracked",
                context_before=classification.context_before,
                event_core=classification.event_core,
                followup_focus=classification.followup_focus,
                causal_memory=classification.causal_memory,
            )
            result["pending_topic"] = self.carryover.get_pending_topic()
        
        elif classification.routing == RoutingType.CASUAL_CHAT:
            # Just update carryover with this turn
            pass
        
        # Add assistant turn if provided
        if assistant_text:
            self._session_turns.append({
                "role": "assistant",
                "text": assistant_text,
                "timestamp": datetime.now().isoformat(),
            })
        
        # Update carryover buffer
        self.carryover.add_turn(
            role="user",
            text=user_text,
            metadata={"classification": classification.routing.value}
        )
        
        if assistant_text:
            self.carryover.add_turn(
                role="assistant",
                text=assistant_text,
                metadata={}
            )
        
        return result
    
    def build_runtime_context(
        self,
        is_new_session: bool = False,
        user_text: str = "",
        agent_persona: str = "阿星"
    ) -> Dict:
        """
        Build runtime context for the agent.
        
        This is called before generating a reply to provide
        continuity context to the agent.
        
        Args:
            is_new_session: Whether this is a /new session
            user_text: The user's current message
            agent_persona: Name of the agent persona
            
        Returns:
            Dict containing:
            - type: "normal" or "new_session_carryover"
            - pending_topic: Current pending topic
            - carryover_turns: Recent conversation turns
            - time_state: Current sleep/wake/active_day state
            - continuity_prompt: Formatted prompt for continuity
            - is_low_info_greeting: Whether user just said hi
        """
        return self.carryover.build_carryover_context(
            is_new_session=is_new_session,
            user_text=user_text,
            agent_persona=agent_persona
        )
    
    def get_carryover_context(
        self,
        user_text: str = "",
        agent_persona: str = "阿星"
    ) -> Dict:
        """
        Get carryover context for /new sessions.
        Convenience method for build_runtime_context(is_new_session=True).
        """
        return self.build_runtime_context(
            is_new_session=True,
            user_text=user_text,
            agent_persona=agent_persona
        )
    
    def get_pending_topics(
        self,
        types: List[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get pending topics.
        Useful for displaying pending items or debugging.
        """
        return self.router.get_pending_topics(types=types, limit=limit)
    
    def resolve_pending_topic(
        self,
        topic_id: Optional[str] = None,
        reason: str = "resolved"
    ) -> Dict:
        """
        Resolve/close a pending topic.
        
        Args:
            topic_id: The topic ID to resolve. If None, resolves current pending.
            reason: Resolution reason ("resolved", "superseded", "explicit_close")
            
        Returns:
            Dict with resolution result
        """
        # Clear from carryover
        self.carryover.clear_pending_topic(topic_id)
        
        # Update status in incidents/staging if needed
        # (For Phase 1, we just clear the carryover)
        
        return {
            "resolved": True,
            "topic_id": topic_id or self.carryover.get_pending_topic().get("id") if self.carryover.get_pending_topic() else None,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
    
    def update_settings(self, updates: Dict) -> Dict:
        """
        Update settings.
        
        Args:
            updates: Dict of settings to update
            
        Returns:
            Dict with updated settings
        """
        # Merge updates
        for key, value in updates.items():
            self.settings[key] = value
        
        self.settings["updated_at"] = datetime.now().isoformat()
        
        # Save to file
        settings_path = self.state_dir / "settings.json"
        settings_path.write_text(json.dumps(self.settings, indent=2, ensure_ascii=False))
        
        # Reload into components
        self.router.settings = self.settings
        self.carryover.settings = self.settings
        
        return self.settings
    
    def get_settings(self) -> Dict:
        """Get current settings"""
        return self.settings
    
    def get_status(self) -> Dict:
        """
        Get overall status of the continuity layer.
        Useful for debugging and status checks.
        """
        pending_topic = self.carryover.get_pending_topic()
        pending_topics = self.get_pending_topics(limit=10)
        carryover_turns = self.carryover.get_turns()
        time_state = self.carryover._evaluate_time_state()
        
        return {
            "continuity_layer": {
                "version": "1.0.0",
                "phase": "Phase 1 - Core Carryover",
                "enabled": self.settings.get("carryover", {}).get("enabled", True),
            },
            "current_session": {
                "is_new_session": self._is_new_session,
                "turn_count": len(self._session_turns),
            },
            "carryover": {
                "has_pending_topic": pending_topic is not None,
                "pending_topic": pending_topic,
                "recent_turns_count": len(carryover_turns),
            },
            "pending_topics": {
                "count": len(pending_topics),
                "items": pending_topics[:5],
            },
            "time_state": time_state,
        }
    
    def write_daily_trace(
        self,
        topic_id: str,
        event_type: str,
        action: str,
        details: Dict
    ) -> str:
        """
        Write a daily memory trace for staged/tracked items.
        
        This creates a structured trace that gets written to the
        daily memory file for auditability.
        
        Args:
            topic_id: The topic ID
            event_type: Type of event
            action: Action taken (created, resolved, updated, etc.)
            details: Additional details
            
        Returns:
            Path to the trace file
        """
        from pathlib import Path
        
        today = datetime.now().strftime("%Y-%m-%d")
        memory_dir = Path("/home/jacky/.openclaw/workspace/memory")
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        trace_file = memory_dir / f"{today}.md"
        
        # Build trace entry
        trace_entry = f"""
## Continuity Trace - {datetime.now().strftime("%H:%M")}

| Field | Value |
|-------|-------|
| Topic ID | {topic_id} |
| Event Type | {event_type} |
| Action | {action} |
| Details | {json.dumps(details, ensure_ascii=False)} |
"""
        
        # Append to daily memory
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(trace_entry)
        
        return str(trace_file)


def main():
    """Test the continuity state manager"""
    state = ContinuityState()
    
    print("=== Continuity State Test ===\n")
    
    # Test 1: Classify a staged message
    print("--- Test 1: Stage a topic ---")
    result = state.handle_message("幫我記住我哋研究緊OCM Sup融合方案")
    print(f"Classification: {result['classification']}")
    print(f"Actions: {result['actions']}")
    print(f"Pending topic: {result['pending_topic']}")
    print()
    
    # Test 2: Build runtime context (normal)
    print("--- Test 2: Normal session context ---")
    context = state.build_runtime_context(is_new_session=False)
    print(f"Type: {context['type']}")
    print()
    
    # Test 3: Build runtime context (/new session)
    print("--- Test 3: /new session context ---")
    context = state.build_runtime_context(
        is_new_session=True,
        user_text="早晨",
        agent_persona="阿星"
    )
    print(f"Type: {context['type']}")
    print(f"Continuity prompt: {context['continuity_prompt']}")
    print(f"Is low-info greeting: {context['is_low_info_greeting']}")
    print()
    
    # Test 4: Get status
    print("--- Test 4: Status ---")
    status = state.get_status()
    print(f"Has pending topic: {status['carryover']['has_pending_topic']}")
    print(f"Time state: {status['time_state']}")
    print()
    
    # Test 5: Resolve pending topic
    print("--- Test 5: Resolve topic ---")
    result = state.resolve_pending_topic(reason="resolved")
    print(f"Resolved: {result}")
    print()
    
    # Test 6: Track a delegated task
    print("--- Test 6: Track delegated task ---")
    result = state.handle_message("麻煩你幫我跟進古洞站項目進度")
    print(f"Classification: {result['classification']}")
    print(f"Actions: {result['actions']}")


if __name__ == "__main__":
    main()
