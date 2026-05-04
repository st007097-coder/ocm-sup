"""
Carryover Manager - /new Session Continuity
==========================================

Handles /new session carryover to reconnect to the right pending topic
instead of collapsing into generic small talk.

Key concepts:
- carryover_turns: Last 3-5 turns of conversation
- pending_topic: The topic that was being discussed
- Carryover selection: Most recent unresolved topic wins
- Low-information guard: Bare "hi" after /new shouldn't collapse into generic chat
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re


@dataclass
class Turn:
    """A conversation turn"""
    role: str  # "user" or "assistant"
    text: str
    timestamp: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class PendingTopic:
    """A pending topic for carryover"""
    id: str
    entity_name: str
    event_type: str
    context_before: Optional[str]
    event_core: str
    followup_focus: str
    causal_memory: Dict
    created: str
    status: str = "active"
    last_accessed: Optional[str] = None


class CarryoverManager:
    """
    Manages /new session carryover.
    
    Responsibilities:
    1. Track recent conversation turns
    2. Identify and track pending topics
    3. Build carryover context for /new sessions
    4. Select most relevant pending topic
    5. Apply low-information guard for bare greetings
    
    Usage:
        carryover = CarryoverManager()
        carryover.add_turn("user", "我哋研究緊OCM Sup融合...")
        context = carryover.build_carryover_context(is_new_session=True)
    """
    
    def __init__(
        self,
        state_dir: str = "/home/jacky/.openclaw/workspace/OCM-Sup/scripts/continuity",
        max_turns: int = 5
    ):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.max_turns = max_turns
        
        # Load or initialize state
        self._init_state()
        
        # Load settings
        self.settings = self._load_settings()
    
    def _init_state(self):
        """Initialize state files"""
        files = {
            "carryover.json": {
                "turns": [],
                "pending_topic": None,
                "pending_topic_id": None,
                "updated": None,
            }
        }
        
        for filename, default_content in files.items():
            filepath = self.state_dir / filename
            if not filepath.exists():
                filepath.write_text(json.dumps(default_content, indent=2, ensure_ascii=False))
    
    def _load_settings(self) -> Dict:
        """Load settings"""
        settings_path = self.state_dir / "settings.json"
        if settings_path.exists():
            try:
                return json.loads(settings_path.read_text())
            except:
                pass
        
        return {
            "carryover": {
                "enabled": True,
                "max_turns": 5,
            },
            "routine_schedule": {
                "timezone": "Asia/Hong_Kong",
                "sleep_time": "00:00",
                "wake_time": "08:30",
            }
        }
    
    def add_turn(self, role: str, text: str, metadata: Optional[Dict] = None):
        """
        Add a conversation turn to the carryover buffer.
        Called after each user/assistant exchange.
        
        Args:
            role: "user" or "assistant"
            text: The message text
            metadata: Optional metadata (intent, entities, etc.)
        """
        filepath = self.state_dir / "carryover.json"
        state = json.loads(filepath.read_text())
        
        now = datetime.now().isoformat()
        
        turn = {
            "role": role,
            "text": text[:500],  # Truncate long messages
            "timestamp": now,
            "metadata": metadata or {},
        }
        
        # Add turn and keep only last max_turns
        turns = state.get("turns", [])
        turns.append(turn)
        
        max_turns = self.settings.get("carryover", {}).get("max_turns", self.max_turns)
        state["turns"] = turns[-max_turns:]
        state["updated"] = now
        
        # If this is a user turn mentioning a pending topic, update it
        if role == "user" and self._looks_like_pending_topic(text):
            # This might be continuing the pending topic
            pass
        
        filepath.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    
    def _looks_like_pending_topic(self, text: str) -> bool:
        """Check if text looks like continuing a pending topic"""
        pending_keywords = [
            "繼續", "跟進", "傾", "討論", "研究",
            "continue", "follow up", "talk about", "discuss",
            "回顧", "睇下", "check",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in pending_keywords)
    
    def set_pending_topic(
        self,
        topic_id: str,
        entity_name: str,
        event_type: str,
        context_before: Optional[str] = None,
        event_core: Optional[str] = None,
        followup_focus: Optional[str] = None,
        causal_memory: Optional[Dict] = None
    ):
        """
        Explicitly set a pending topic for carryover.
        Called when user parks a topic or we classify something as staged/tracked.
        
        Args:
            topic_id: Unique ID for this pending topic
            entity_name: Name of the entity/topic
            event_type: Type of event (parked_topic, delegated_task, etc.)
            context_before: Context before this topic
            event_core: The core of what was discussed
            followup_focus: What to focus on in follow-up
            causal_memory: Structured causal memory dict
        """
        filepath = self.state_dir / "carryover.json"
        state = json.loads(filepath.read_text())
        
        now = datetime.now().isoformat()
        
        pending_topic = {
            "id": topic_id,
            "entity_name": entity_name,
            "event_type": event_type,
            "context_before": context_before,
            "event_core": event_core or entity_name,
            "followup_focus": followup_focus or f"回顧：{entity_name}",
            "causal_memory": causal_memory or {},
            "created": now,
            "status": "active",
            "last_accessed": now,
        }
        
        state["pending_topic"] = pending_topic
        state["pending_topic_id"] = topic_id
        state["updated"] = now
        
        filepath.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    
    def clear_pending_topic(self, topic_id: Optional[str] = None):
        """
        Clear the pending topic.
        Called when a topic is resolved or explicitly closed.
        
        Args:
            topic_id: Optional topic ID to clear. If None, clears current pending topic.
        """
        filepath = self.state_dir / "carryover.json"
        state = json.loads(filepath.read_text())
        
        if topic_id is None or state.get("pending_topic_id") == topic_id:
            state["pending_topic"] = None
            state["pending_topic_id"] = None
            state["updated"] = datetime.now().isoformat()
            filepath.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    
    def get_pending_topic(self) -> Optional[Dict]:
        """Get the current pending topic"""
        filepath = self.state_dir / "carryover.json"
        state = json.loads(filepath.read_text())
        return state.get("pending_topic")
    
    def get_turns(self) -> List[Dict]:
        """Get recent conversation turns"""
        filepath = self.state_dir / "carryover.json"
        state = json.loads(filepath.read_text())
        return state.get("turns", [])
    
    def build_carryover_context(
        self,
        is_new_session: bool = False,
        user_text: str = "",
        agent_persona: str = "阿星"
    ) -> Dict:
        """
        Build carryover context for agent reply generation.
        
        Args:
            is_new_session: True if this is a /new session
            user_text: The user's message in this turn
            agent_persona: Name of the agent persona
            
        Returns:
            Dict containing:
            - type: "normal" or "new_session_carryover"
            - pending_topic: The pending topic info
            - carryover_turns: Recent turns for context
            - time_state: Current sleep/wake/active_day state
            - continuity_prompt: Formatted prompt for the agent
            - is_low_info_greeting: True if user just said hi/hey
        """
        filepath = self.state_dir / "carryover.json"
        state = json.loads(filepath.read_text())
        
        # Check if this is a low-information greeting
        is_low_info = self._is_low_information_greeting(user_text)
        
        if not is_new_session:
            return {
                "type": "normal",
                "pending_topic": None,
                "carryover_turns": state.get("turns", []),
                "time_state": self._evaluate_time_state(),
                "is_low_info_greeting": False,
                "continuity_prompt": None,
            }
        
        # This is a /new session - build carryover context
        pending_topic = state.get("pending_topic")
        
        # Build continuity prompt
        continuity_prompt = self._build_continuity_prompt(
            pending_topic=pending_topic,
            turns=state.get("turns", []),
            agent_persona=agent_persona,
            is_low_info_greeting=is_low_info
        )
        
        # Update last accessed time
        if pending_topic:
            pending_topic["last_accessed"] = datetime.now().isoformat()
            state["pending_topic"] = pending_topic
            filepath.write_text(json.dumps(state, indent=2, ensure_ascii=False))
        
        return {
            "type": "new_session_carryover",
            "pending_topic": pending_topic,
            "carryover_turns": state.get("turns", []),
            "time_state": self._evaluate_time_state(),
            "is_low_info_greeting": is_low_info,
            "continuity_prompt": continuity_prompt,
        }
    
    def _is_low_information_greeting(self, text: str) -> bool:
        """Check if text is a low-information greeting"""
        if not text:
            return True
        
        text_lower = text.lower().strip()
        
        low_info_patterns = [
            r"^hi$",
            r"^hey$", 
            r"^你好$",
            r"^早晨$",
            r"^晚安$",
            r"^hello$",
            r"^hi\s*",
            r"^hey\s*",
            r"^你好\s*",
            r"^早晨\s*",
            r"^喂$",
            r"^係$",
            r"^在$",
        ]
        
        for pattern in low_info_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Also check for very short messages (< 5 chars)
        if len(text.strip()) < 5:
            return True
        
        return False
    
    def _build_continuity_prompt(
        self,
        pending_topic: Optional[Dict],
        turns: List[Dict],
        agent_persona: str,
        is_low_info_greeting: bool
    ) -> str:
        """
        Build a natural continuity prompt for the agent.
        
        The prompt should:
        1. Reference the pending topic naturally
        2. Not be too verbose or robotic
        3. Help the agent continue the conversation naturally
        4. Respect the low-information greeting guard
        """
        if not pending_topic:
            # No pending topic - just a normal greeting
            if is_low_info_greeting:
                return f"{agent_persona}，早晨。你想傾乜？"
            return None
        
        # Build context from pending topic
        event_type = pending_topic.get("event_type", "parked_topic")
        followup_focus = pending_topic.get("followup_focus", "")
        entity_name = pending_topic.get("entity_name", "")
        
        # Build appropriate continuity text based on event type
        if event_type == "parked_topic":
            continuity_text = f"我記得你之前提到想討論「{entity_name}」，"
        elif event_type == "delegated_task":
            continuity_text = f"你之前交代咗個任務關於「{entity_name}」，"
        elif event_type == "watchful_state":
            continuity_text = f"你之前提到「{entity_name}」，"
        elif event_type == "sensitive_event":
            continuity_text = f"你之前提醒我要關注「{entity_name}」，"
        else:
            continuity_text = f"關於「{entity_name}」，"
        
        # If it's a low-information greeting, keep it short
        if is_low_info_greeting:
            return f"{continuity_text}你想繼續傾嗎？"
        
        # Normal case - provide more context
        return f"{continuity_text}{followup_focus}。"
    
    def _evaluate_time_state(self) -> Dict:
        """
        Evaluate current time state (sleep/wake/active_day).
        Used to suppress follow-ups during sleep hours.
        """
        schedule = self.settings.get("routine_schedule", {})
        sleep_time = schedule.get("sleep_time", "00:00")
        wake_time = schedule.get("wake_time", "08:30")
        timezone = schedule.get("timezone", "Asia/Hong_Kong")
        
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        # Parse times
        sleep_parts = sleep_time.split(":")
        wake_parts = wake_time.split(":")
        sleep_minutes = int(sleep_parts[0]) * 60 + int(sleep_parts[1])
        wake_minutes = int(wake_parts[0]) * 60 + int(wake_parts[1])
        
        current_minutes = now.hour * 60 + now.minute
        
        # Determine phase
        # Sleep crosses midnight if sleep_time > wake_time (e.g., 00:00 to 08:30)
        # Normal case: sleep_time < wake_time (e.g., 23:00 to 07:00)
        if sleep_minutes > wake_minutes:
            # Sleep crosses midnight (e.g., 00:00 to 08:30)
            # is_sleep when: current >= sleep_minutes (00:00+) OR current < wake_minutes (<08:30)
            is_sleep = current_minutes >= sleep_minutes or current_minutes < wake_minutes
        else:
            # Normal case (e.g., 23:00 to 07:00)
            # is_sleep when: current >= sleep_minutes AND current < wake_minutes
            is_sleep = sleep_minutes <= current_minutes < wake_minutes
        
        phase = "sleep" if is_sleep else "active_day"
        
        return {
            "phase": phase,
            "current_time": current_time_str,
            "timezone": timezone,
            "sleep_time": sleep_time,
            "wake_time": wake_time,
            "is_proactive_allowed": not is_sleep,
        }
    
    def summarize_turns(self, turns: List[Dict], max_turns: int = 3) -> str:
        """
        Summarize recent turns for context.
        Used when building carryover context.
        """
        if not turns:
            return ""
        
        recent = turns[-max_turns:]
        lines = []
        
        for turn in recent:
            role = "你" if turn.get("role") == "user" else "我"
            text = turn.get("text", "")[:100]
            if len(turn.get("text", "")) > 100:
                text += "..."
            lines.append(f"{role}：{text}")
        
        return " | ".join(lines)


def main():
    """Test the carryover manager"""
    manager = CarryoverManager()
    
    print("=== Carryover Manager Test ===\n")
    
    # Simulate conversation
    manager.add_turn("user", "我哋研究緊OCM Sup同openclaw-continuity融合方案")
    manager.add_turn("assistant", "好主意！openclaw-continuity有啲幾好用嘅概念...")
    manager.add_turn("user", "幫我記住呢個研究主題")
    
    # Set pending topic
    manager.set_pending_topic(
        topic_id="research_ocm_sup_continuity",
        entity_name="OCM Sup + openclaw-continuity 融合研究",
        event_type="parked_topic",
        context_before="討論緊融合方案",
        event_core="融合方案研究",
        followup_focus="繼續分析融合方案",
    )
    
    # Test normal context
    print("--- Normal Session Context ---")
    context = manager.build_carryover_context(is_new_session=False)
    print(f"Type: {context['type']}")
    print(f"Pending topic: {context['pending_topic']}")
    print()
    
    # Test /new session context
    print("--- /new Session Context ---")
    context = manager.build_carryover_context(
        is_new_session=True,
        user_text="早晨",
        agent_persona="阿星"
    )
    print(f"Type: {context['type']}")
    print(f"Pending topic: {context['pending_topic']}")
    print(f"Continuity prompt: {context['continuity_prompt']}")
    print(f"Is low-info greeting: {context['is_low_info_greeting']}")
    print()
    
    # Test /new with full greeting
    print("--- /new Session with Full Message ---")
    context = manager.build_carryover_context(
        is_new_session=True,
        user_text="早晨！我哋之前研究緊OCM Sup融合，繼續傾",
        agent_persona="阿星"
    )
    print(f"Is low-info greeting: {context['is_low_info_greeting']}")
    print(f"Continuity prompt: {context['continuity_prompt']}")
    print()
    
    # Test time state
    print("--- Time State ---")
    print(f"Time state: {context['time_state']}")


if __name__ == "__main__":
    main()
