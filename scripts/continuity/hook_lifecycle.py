"""
Hook Lifecycle Manager
=====================

Manages the follow-up hook lifecycle:
- due: Check if a hook is due for follow-up
- render: Render the follow-up message
- complete: Close/resolve a hook

Hook states:
- active: Currently being tracked
- due: Ready to send follow-up
- dispatched: Sent to user, waiting for reply
- parked: Temporarily suspended (due to cooldown/sleep)
- closed: Resolved or explicitly closed

Policy controls:
- re_engagement: wait_for_reply or timed_retry
- cooldown: Minimum time between dispatches
- sleep_suppress: Don't disturb during sleep hours
- dispatch_cap: Maximum dispatches per day
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

try:
    from .carryover import CarryoverManager
except ImportError:
    from carryover import CarryoverManager


class HookStatus(Enum):
    """Hook lifecycle status"""
    ACTIVE = "active"
    DUE = "due"
    DISPATCHED = "dispatched"
    PARKED = "parked"
    CLOSED = "closed"


class ClosureReason(Enum):
    """Why a hook was closed"""
    RESOLVED = "resolved"
    USER_REPLY = "user_reply"
    SUPERSEDED = "superseded"
    EXPLICIT_CLOSE = "explicit_close"
    MAX_UNANSWERED = "max_unanswered"
    EXPIRED = "expired"


@dataclass
class Hook:
    """A follow-up hook"""
    id: str
    incident_id: str
    entity_name: str
    event_type: str
    followup_focus: str
    causal_memory: Dict
    created: str
    status: str = "active"
    last_due_check: Optional[str] = None
    last_dispatch: Optional[str] = None
    dispatch_count: int = 0
    cooldown_until: Optional[str] = None
    parked_until: Optional[str] = None
    closure_reason: Optional[str] = None
    closure_time: Optional[str] = None


class HookLifecycle:
    """
    Manages follow-up hook lifecycle.
    
    Usage:
        lifecycle = HookLifecycle(state_dir="/path/to/continuity")
        
        # Create a hook from an incident
        hook_id = lifecycle.create_hook(incident_id, incident_data)
        
        # Check if any hooks are due
        due_hooks = lifecycle.check_due_hooks()
        
        # Render a follow-up message
        message = lifecycle.render_followup(hook_id)
        
        # Mark as dispatched
        lifecycle.mark_dispatched(hook_id)
        
        # Close a hook
        lifecycle.close_hook(hook_id, reason="resolved")
    """
    
    def __init__(
        self,
        state_dir: str = "/home/jacky/.openclaw/workspace/OCM-Sup/scripts/continuity",
        carryover_manager: Optional[CarryoverManager] = None
    ):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize carryover manager if not provided
        self.carryover = carryover_manager or CarryoverManager(state_dir=str(self.state_dir))
        
        # Load settings
        self.settings = self._load_settings()
        
        # Initialize state
        self._init_state()
    
    def _init_state(self):
        """Initialize state files"""
        hooks_path = self.state_dir / "hooks.json"
        if not hooks_path.exists():
            hooks_path.write_text(json.dumps({"items": [], "updated": None}, indent=2))
    
    def _load_settings(self) -> Dict:
        """Load settings"""
        settings_path = self.state_dir / "settings.json"
        if settings_path.exists():
            try:
                return json.loads(settings_path.read_text())
            except:
                pass
        
        return self._default_settings()
    
    def _default_settings(self) -> Dict:
        """Default settings"""
        return {
            "re_engagement": {
                "mode": "wait_for_reply",  # or "timed_retry"
                "retry_after_hours": 4,
                "max_unanswered_before_park": 2,
            },
            "dispatch": {
                "cooldown_minutes": 30,
                "cap": 10,
            },
            "sleep_rest_suppress": {
                "enabled": True,
                "duration_hours": 4,
                "auto_clear_hours": 0,
            },
            "closure": {
                "auto_close_on_user_reply": True,
            },
        }
    
    def _now(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()
    
    def _parse_time(self, time_str: str) -> datetime:
        """Parse ISO timestamp"""
        return datetime.fromisoformat(time_str)
    
    def _hours_ago(self, hours: float) -> datetime:
        """Get datetime N hours ago"""
        return datetime.now() - timedelta(hours=hours)
    
    def create_hook(
        self,
        incident_id: str,
        entity_name: str,
        event_type: str,
        followup_focus: str,
        causal_memory: Dict
    ) -> str:
        """
        Create a new hook from an incident.
        
        Args:
            incident_id: The incident ID this hook is for
            entity_name: Name of the entity/topic
            event_type: Type of event
            followup_focus: What to follow up on
            causal_memory: Causal memory dict
            
        Returns:
            The new hook ID
        """
        import uuid
        
        hook_id = f"hook_{uuid.uuid4().hex[:8]}"
        
        hook = {
            "id": hook_id,
            "incident_id": incident_id,
            "entity_name": entity_name,
            "event_type": event_type,
            "followup_focus": followup_focus,
            "causal_memory": causal_memory,
            "created": self._now(),
            "status": HookStatus.ACTIVE.value,
            "last_due_check": None,
            "last_dispatch": None,
            "dispatch_count": 0,
            "cooldown_until": None,
            "parked_until": None,
            "closure_reason": None,
            "closure_time": None,
        }
        
        # Load hooks
        hooks_path = self.state_dir / "hooks.json"
        hooks_data = json.loads(hooks_path.read_text())
        
        # Add hook
        hooks_data["items"].append(hook)
        hooks_data["updated"] = self._now()
        
        # Save
        hooks_path.write_text(json.dumps(hooks_data, indent=2, ensure_ascii=False))
        
        return hook_id
    
    def get_hook(self, hook_id: str) -> Optional[Dict]:
        """Get a hook by ID"""
        hooks_path = self.state_dir / "hooks.json"
        hooks_data = json.loads(hooks_path.read_text())
        
        for hook in hooks_data.get("items", []):
            if hook["id"] == hook_id:
                return hook
        
        return None
    
    def get_active_hooks(self) -> List[Dict]:
        """Get all active hooks"""
        hooks_path = self.state_dir / "hooks.json"
        hooks_data = json.loads(hooks_path.read_text())
        
        return [
            h for h in hooks_data.get("items", [])
            if h["status"] in [HookStatus.ACTIVE.value, HookStatus.DUE.value]
        ]
    
    def check_due_hooks(self) -> List[Dict]:
        """
        Check all hooks and return those that are due.
        
        A hook is due if:
        1. It's active
        2. It's not in cooldown
        3. It's not parked (sleep suppress)
        4. Time conditions are met
        
        Returns:
            List of hooks that are due
        """
        hooks_path = self.state_dir / "hooks.json"
        hooks_data = json.loads(hooks_path.read_text())
        
        due_hooks = []
        
        for hook in hooks_data.get("items", []):
            if hook["status"] in [HookStatus.CLOSED.value, HookStatus.PARKED.value]:
                continue
            
            is_due, reason = self._is_hook_due(hook)
            
            if is_due:
                # Update status to DUE
                hook["status"] = HookStatus.DUE.value
                hook["last_due_check"] = self._now()
                due_hooks.append(hook)
        
        # Save updates
        hooks_path.write_text(json.dumps(hooks_data, indent=2, ensure_ascii=False))
        
        return due_hooks
    
    def _is_hook_due(self, hook: Dict) -> Tuple[bool, str]:
        """
        Check if a single hook is due.
        
        Returns:
            Tuple of (is_due, reason)
        """
        # Check cooldown
        if hook.get("cooldown_until"):
            cooldown_until = self._parse_time(hook["cooldown_until"])
            if datetime.now() < cooldown_until:
                return False, "in_cooldown"
        
        # Check parked (sleep suppress)
        if hook.get("parked_until"):
            parked_until = self._parse_time(hook["parked_until"])
            if datetime.now() < parked_until:
                return False, "parked"
        
        # Check dispatch cap
        dispatch_cap = self.settings.get("dispatch", {}).get("cap", 10)
        if hook.get("dispatch_count", 0) >= dispatch_cap:
            return False, "dispatch_cap_reached"
        
        # Check max unanswered
        max_unanswered = self.settings.get("re_engagement", {}).get("max_unanswered_before_park", 2)
        if hook.get("dispatch_count", 0) >= max_unanswered and hook["status"] == HookStatus.DISPATCHED.value:
            # Park it
            self._park_hook(hook, reason="max_unanswered")
            return False, "parked_max_unanswered"
        
        # Check re-engagement mode
        re_engagement_mode = self.settings.get("re_engagement", {}).get("mode", "wait_for_reply")
        
        if re_engagement_mode == "timed_retry":
            # Check if retry time has passed
            retry_after_hours = self.settings.get("re_engagement", {}).get("retry_after_hours", 4)
            if hook.get("last_dispatch"):
                last_dispatch = self._parse_time(hook["last_dispatch"])
                if datetime.now() < last_dispatch + timedelta(hours=retry_after_hours):
                    return False, "retry_not_due"
        
        # Hook is due
        return True, "ready"
    
    def _park_hook(self, hook: Dict, reason: str = "sleep_suppress"):
        """Park a hook (temporarily suspend)"""
        hooks_path = self.state_dir / "hooks.json"
        hooks_data = json.loads(hooks_path.read_text())
        
        for h in hooks_data.get("items", []):
            if h["id"] == hook["id"]:
                h["status"] = HookStatus.PARKED.value
                h["parked_until"] = (datetime.now() + timedelta(hours=4)).isoformat()
                break
        
        hooks_data["updated"] = self._now()
        hooks_path.write_text(json.dumps(hooks_data, indent=2, ensure_ascii=False))
    
    def render_followup(self, hook_id: str) -> Optional[str]:
        """
        Render a follow-up message for a hook.
        
        Args:
            hook_id: The hook ID
            
        Returns:
            The rendered follow-up message, or None if hook not found
        """
        hook = self.get_hook(hook_id)
        if not hook:
            return None
        
        # Build context from causal memory
        causal = hook.get("causal_memory", {})
        
        # Get time anchor
        time_anchor = causal.get("time_anchor", "")
        
        # Get followup focus
        followup_focus = hook.get("followup_focus", "")
        
        # Get event type for appropriate wording
        event_type = hook.get("event_type", "parked_topic")
        
        # Build the message
        if event_type == "delegated_task":
            message = f"想提醒你之前交代嘅任務：{followup_focus}"
        elif event_type == "watchful_state":
            message = f"留意到你之前提到「{hook.get('entity_name', '')}」，情況點樣？"
        elif event_type == "sensitive_event":
            message = f"跟進你之前關注嘅事項：{followup_focus}"
        else:  # parked_topic
            message = f"你之前暫存咗個話題關於「{hook.get('entity_name', '')}」，你想繼續傾嗎？"
        
        # Add time context if available
        if time_anchor:
            message += f"\n\n（上次傾呢個係 {time_anchor}）"
        
        return message
    
    def mark_dispatched(self, hook_id: str):
        """
        Mark a hook as dispatched (message sent).
        
        Args:
            hook_id: The hook ID
        """
        hooks_path = self.state_dir / "hooks.json"
        hooks_data = json.loads(hooks_path.read_text())
        
        for hook in hooks_data.get("items", []):
            if hook["id"] == hook_id:
                hook["status"] = HookStatus.DISPATCHED.value
                hook["last_dispatch"] = self._now()
                hook["dispatch_count"] = hook.get("dispatch_count", 0) + 1
                
                # Set cooldown
                cooldown_minutes = self.settings.get("dispatch", {}).get("cooldown_minutes", 30)
                hook["cooldown_until"] = (datetime.now() + timedelta(minutes=cooldown_minutes)).isoformat()
                
                # Clear parked status if any
                hook["parked_until"] = None
                break
        
        hooks_data["updated"] = self._now()
        hooks_path.write_text(json.dumps(hooks_data, indent=2, ensure_ascii=False))
    
    def close_hook(
        self,
        hook_id: str,
        reason: str = ClosureReason.RESOLVED.value
    ):
        """
        Close a hook.
        
        Args:
            hook_id: The hook ID
            reason: Closure reason
        """
        hooks_path = self.state_dir / "hooks.json"
        hooks_data = json.loads(hooks_path.read_text())
        
        for hook in hooks_data.get("items", []):
            if hook["id"] == hook_id:
                hook["status"] = HookStatus.CLOSED.value
                hook["closure_reason"] = reason
                hook["closure_time"] = self._now()
                
                # Also update the incident
                self._close_incident(hook.get("incident_id"), reason)
                break
        
        hooks_data["updated"] = self._now()
        hooks_path.write_text(json.dumps(hooks_data, indent=2, ensure_ascii=False))
    
    def _close_incident(self, incident_id: str, reason: str):
        """Close the associated incident"""
        if not incident_id:
            return
        
        incidents_path = self.state_dir / "incidents.json"
        if not incidents_path.exists():
            return
        
        incidents = json.loads(incidents_path.read_text())
        
        for incident in incidents.get("items", []):
            if incident.get("id") == incident_id:
                incident["status"] = "closed"
                incident["closure_reason"] = reason
                incident["closure_time"] = self._now()
                break
        
        incidents["updated"] = self._now()
        incidents_path.write_text(json.dumps(incidents, indent=2, ensure_ascii=False))
    
    def check_and_apply_sleep_suppress(self):
        """
        Check current time and park/unpark hooks based on sleep schedule.
        
        This should be called periodically (e.g., by a cron job).
        """
        time_state = self.carryover._evaluate_time_state()
        phase = time_state.get("phase", "active_day")
        
        hooks_path = self.state_dir / "hooks.json"
        hooks_data = json.loads(hooks_path.read_text())
        
        for hook in hooks_data.get("items", []):
            if hook["status"] == HookStatus.CLOSED.value:
                continue
            
            if phase == "sleep":
                # Park active hooks during sleep
                if hook["status"] in [HookStatus.ACTIVE.value, HookStatus.DUE.value]:
                    sleep_duration = self.settings.get("sleep_rest_suppress", {}).get("duration_hours", 4)
                    hook["status"] = HookStatus.PARKED.value
                    hook["parked_until"] = (datetime.now() + timedelta(hours=sleep_duration)).isoformat()
            
            elif phase == "active_day":
                # Unpark hooks when active
                if hook["status"] == HookStatus.PARKED.value:
                    # Check if parked_until has passed
                    if hook.get("parked_until"):
                        parked_until = self._parse_time(hook["parked_until"])
                        if datetime.now() >= parked_until:
                            hook["status"] = HookStatus.ACTIVE.value
                            hook["parked_until"] = None
        
        hooks_data["updated"] = self._now()
        hooks_path.write_text(json.dumps(hooks_data, indent=2, ensure_ascii=False))
    
    def get_dispatch_stats(self) -> Dict:
        """
        Get dispatch statistics for today.
        
        Returns:
            Dict with dispatch counts and limits
        """
        hooks_path = self.state_dir / "hooks.json"
        hooks_data = json.loads(hooks_path.read_text())
        
        today = datetime.now().date()
        
        dispatches_today = 0
        for hook in hooks_data.get("items", []):
            if hook.get("last_dispatch"):
                dispatch_date = self._parse_time(hook["last_dispatch"]).date()
                if dispatch_date == today:
                    dispatches_today += 1
        
        cap = self.settings.get("dispatch", {}).get("cap", 10)
        
        return {
            "dispatches_today": dispatches_today,
            "cap": cap,
            "remaining": max(0, cap - dispatches_today),
        }


def main():
    """Test the hook lifecycle"""
    lifecycle = HookLifecycle()
    
    print("=== Hook Lifecycle Test ===\n")
    
    # Create a hook
    print("--- Create Hook ---")
    hook_id = lifecycle.create_hook(
        incident_id="incident_test_001",
        entity_name="OCM Sup 融合研究",
        event_type="delegated_task",
        followup_focus="繼續分析融合方案",
        causal_memory={
            "facts": ["OCM Sup + openclaw-continuity 融合"],
            "state": "delegated",
            "time_anchor": "2026-04-24 14:00",
        }
    )
    print(f"Created hook: {hook_id}")
    print()
    
    # Check due hooks
    print("--- Check Due Hooks ---")
    due_hooks = lifecycle.check_due_hooks()
    print(f"Due hooks: {len(due_hooks)}")
    for h in due_hooks:
        print(f"  - {h['id']}: {h['entity_name']}")
    print()
    
    # Render followup
    if due_hooks:
        print("--- Render Followup ---")
        message = lifecycle.render_followup(due_hooks[0]["id"])
        print(f"Message: {message}")
        print()
    
    # Check dispatch stats
    print("--- Dispatch Stats ---")
    stats = lifecycle.get_dispatch_stats()
    print(f"Today: {stats['dispatches_today']} / {stats['cap']}")
    print()
    
    # Sleep suppress check
    print("--- Sleep Suppress ---")
    time_state = lifecycle.carryover._evaluate_time_state()
    print(f"Current phase: {time_state['phase']}")
    lifecycle.check_and_apply_sleep_suppress()
    print()


if __name__ == "__main__":
    main()
