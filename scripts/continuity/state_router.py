"""
State Router - Message Classification
=====================================

Routes incoming user messages into three categories:
- casual_chat: No tracking needed, direct reply
- staged_memory: Temporarily parked for later
- tracked_followup: Formally tracked with follow-up hooks

Supports four event types for tracked items:
- parked_topic: Topic parked for later discussion
- watchful_state: Emotional/physical state to monitor
- delegated_task: Task delegated for later follow-up
- sensitive_event: Sensitive event requiring continuity
"""

import re
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict
import json


class RoutingType(Enum):
    """Three routing types for messages"""
    CASUAL_CHAT = "casual_chat"
    STAGED_MEMORY = "staged_memory"
    TRACKED_FOLLOWUP = "tracked_followup"


class EventType(Enum):
    """Four tracked event types"""
    PARKED_TOPIC = "parked_topic"
    WATCHFUL_STATE = "watchful_state"
    DELEGATED_TASK = "delegated_task"
    SENSITIVE_EVENT = "sensitive_event"


@dataclass
class MessageClassification:
    """Result of message classification"""
    routing: RoutingType
    event_type: Optional[EventType] = None
    confidence: float = 1.0
    entity_name: Optional[str] = None
    context_before: Optional[str] = None
    event_core: Optional[str] = None
    followup_focus: Optional[str] = None
    causal_memory: Dict = field(default_factory=dict)


class StateRouter:
    """
    Routes incoming messages into appropriate routing type.
    
    Usage:
        router = StateRouter(wiki_path="/path/to/wiki")
        classification = router.classify("幫我記住...")  # Returns MessageClassification
    """
    
    # Keywords that indicate staging/tracking intent
    STAGING_KEYWORDS = [
        # English
        "remember this", "park this", "hold this", "track this",
        "remind me", "follow up", "get back to me",
        # Traditional Chinese
        "幫我記住", "暫存", "記住呢個", "跟進", "提醒我",
        "遲啲再聊", "晚啲再傾", "遲啲再講",
        # Simplified Chinese
        "帮我记住", "暂存", "记住这个", "跟进", "提醒我",
        "迟点再聊", "晚点再倾", "迟点再讲",
    ]
    
    TRACKING_KEYWORDS = [
        # English
        "don't forget", "make sure to", "i need you to",
        "it's important that", "watch for", "monitor",
        # Traditional Chinese
        "唔好忘記", "記得", "記住", "一定要",
        "留意住", "監察住", "跟蹤",
        # Simplified Chinese
        "不要忘记", "记得", "记住", "一定要",
        "留意住", "监察住", "跟踪",
    ]
    
    WATCHFUL_KEYWORDS = [
        # English
        "feeling", "not feeling well", "feeling sick",
        "having trouble", "struggling with",
        # Traditional Chinese  
        "覺得", "感覺", "身體", "有啲唔舒服",
        "困擾", "擔心", "關注住",
        # Simplified Chinese
        "觉得", "感觉", "身体", "有点不舒服",
        "困扰", "担心", "关注住",
    ]
    
    DELEGATED_TASK_KEYWORDS = [
        # English
        "can you", "please", "could you", "i want you to",
        "when you have time", "when you get a chance",
        # Traditional Chinese
        "你可唔可以", "麻煩你", "麻煩幫手",
        "得閒時", "有時間嘅時候", "幫我",
        "跟進", "追蹤", "監察", "留意住",
        # Simplified Chinese
        "你可不可以", "麻烦你", "麻烦帮手",
        "得闲时", "有时间的时候", "帮我",
        "跟进", "追踪", "监察", "留意住",
    ]
    
    SENSITIVE_KEYWORDS = [
        # English
        "confidential", "private", "don't share this",
        "sensitive", "personal matter",
        # Traditional Chinese
        "保密", "私密", "唔好話俾其他人知",
        "私人", "敏感",
        # Simplified Chinese
        "保密", "私密", "不要话给别人知",
        "私人", "敏感",
    ]
    
    def __init__(
        self,
        wiki_path: str = "/home/jacky/.openclaw/workspace/wiki",
        state_dir: str = "/home/jacky/.openclaw/workspace/OCM-Sup/scripts/continuity"
    ):
        self.wiki_path = Path(wiki_path)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Load settings
        self.settings = self._load_settings()
        
        # Causal memory cache
        self._causal_memory_cache: Dict = {}
        
        # Initialize state files
        self._init_state_files()
    
    def _load_settings(self) -> Dict:
        """Load settings from state file"""
        settings_path = self.state_dir / "settings.json"
        if settings_path.exists():
            try:
                return json.loads(settings_path.read_text())
            except:
                pass
        
        # Default settings
        return {
            "routine_schedule": {
                "timezone": "Asia/Hong_Kong",
                "sleep_time": "00:00",
                "wake_time": "08:30",
            },
            "carryover": {
                "enabled": True,
                "max_turns": 5,
            },
            "causal_memory": {
                "summary_max_facts": 3,
                "include_time_anchor": True,
                "include_state_marker": True,
            }
        }
    
    def _init_state_files(self):
        """Initialize state files if they don't exist"""
        files = {
            "staging.json": {"items": [], "updated": None},
            "incidents.json": {"items": [], "updated": None},
            "hooks.json": {"items": [], "updated": None},
            "carryover.json": {"turns": [], "pending_topic": None, "updated": None},
        }
        
        for filename, default_content in files.items():
            filepath = self.state_dir / filename
            if not filepath.exists():
                filepath.write_text(json.dumps(default_content, indent=2, ensure_ascii=False))
    
    def classify(self, user_text: str, context: Optional[Dict] = None) -> MessageClassification:
        """
        Classify a user message into routing type.
        
        Args:
            user_text: The user's message
            context: Optional context (previous turns, etc.)
            
        Returns:
            MessageClassification with routing type and metadata
        """
        user_text_lower = user_text.lower().strip()
        
        # Check for delegated task FIRST (more specific than staging)
        # "麻煩你幫我跟進" should be delegated task, not staged
        if self._matches_keywords(user_text_lower, self.DELEGATED_TASK_KEYWORDS):
            return self._classify_delegated(user_text, context)
        
        # Check for watchful state
        if self._matches_keywords(user_text_lower, self.WATCHFUL_KEYWORDS):
            return self._classify_watchful(user_text, context)
        
        # Check for tracking keywords
        if self._matches_keywords(user_text_lower, self.TRACKING_KEYWORDS):
            return self._classify_tracking(user_text, context)
        
        # Check for staging keywords (park for later)
        if self._matches_keywords(user_text_lower, self.STAGING_KEYWORDS):
            return self._classify_staging(user_text, context)
        
        # Check for sensitive event
        if self._matches_keywords(user_text_lower, self.SENSITIVE_KEYWORDS):
            return self._classify_sensitive(user_text, context)
        
        # Default: casual chat
        return MessageClassification(
            routing=RoutingType.CASUAL_CHAT,
            confidence=1.0
        )
    
    def _matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text matches any of the keywords"""
        for keyword in keywords:
            if keyword.lower() in text:
                return True
        return False
    
    def _classify_staging(self, user_text: str, context: Optional[Dict]) -> MessageClassification:
        """Classify as staged memory (parked topic)"""
        # Extract topic from user text
        topic = self._extract_topic(user_text)
        
        causal = {
            "facts": [topic],
            "state": "staged",
            "open_loop": topic,
            "time_anchor": self._get_time_anchor(),
        }
        
        return MessageClassification(
            routing=RoutingType.STAGED_MEMORY,
            event_type=EventType.PARKED_TOPIC,
            confidence=0.8,
            entity_name=topic,
            context_before=context.get("recent_topic") if context else None,
            event_core=topic,
            followup_focus=f"回顧：{topic}",
            causal_memory=causal
        )
    
    def _classify_tracking(self, user_text: str, context: Optional[Dict]) -> MessageClassification:
        """Classify as tracked followup"""
        topic = self._extract_topic(user_text)
        
        causal = {
            "facts": [topic],
            "state": "tracked",
            "open_loop": topic,
            "time_anchor": self._get_time_anchor(),
            "followup_focus_code": "explicit_reminder",
        }
        
        return MessageClassification(
            routing=RoutingType.TRACKED_FOLLOWUP,
            event_type=EventType.PARKED_TOPIC,
            confidence=0.9,
            entity_name=topic,
            context_before=context.get("recent_topic") if context else None,
            event_core=topic,
            followup_focus=f"提醒：{topic}",
            causal_memory=causal
        )
    
    def _classify_watchful(self, user_text: str, context: Optional[Dict]) -> MessageClassification:
        """Classify as watchful state"""
        state = self._extract_state(user_text)
        
        causal = {
            "facts": [state],
            "state": "watchful",
            "open_loop": state,
            "time_anchor": self._get_time_anchor(),
            "state_marker": state,
        }
        
        return MessageClassification(
            routing=RoutingType.TRACKED_FOLLOWUP,
            event_type=EventType.WATCHFUL_STATE,
            confidence=0.85,
            entity_name=state,
            event_core=state,
            followup_focus=f"關注：{state}",
            causal_memory=causal
        )
    
    def _classify_delegated(self, user_text: str, context: Optional[Dict]) -> MessageClassification:
        """Classify as delegated task"""
        task = self._extract_task(user_text)
        
        causal = {
            "facts": [task],
            "state": "delegated",
            "open_loop": task,
            "time_anchor": self._get_time_anchor(),
            "followup_focus_code": "task_delegation",
        }
        
        return MessageClassification(
            routing=RoutingType.TRACKED_FOLLOWUP,
            event_type=EventType.DELEGATED_TASK,
            confidence=0.9,
            entity_name=task,
            event_core=task,
            followup_focus=f"跟進任務：{task}",
            causal_memory=causal
        )
    
    def _classify_sensitive(self, user_text: str, context: Optional[Dict]) -> MessageClassification:
        """Classify as sensitive event"""
        event = self._extract_event(user_text)
        
        causal = {
            "facts": [event],
            "state": "sensitive",
            "open_loop": event,
            "time_anchor": self._get_time_anchor(),
            "writeback_policy": "require_explicit_resolution",
        }
        
        return MessageClassification(
            routing=RoutingType.TRACKED_FOLLOWUP,
            event_type=EventType.SENSITIVE_EVENT,
            confidence=0.95,
            entity_name=event,
            event_core=event,
            followup_focus=f"持續關注：{event}",
            causal_memory=causal
        )
    
    def _extract_topic(self, text: str) -> str:
        """Extract the main topic from user text"""
        # Remove common prefixes
        text = re.sub(r"^(記住|remind me|帮我记住|提醒我|park|track)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(關於|concerning|关于)", "", text, flags=re.IGNORECASE)
        text = text.strip()
        # Truncate if too long
        if len(text) > 100:
            text = text[:100] + "..."
        return text
    
    def _extract_state(self, text: str) -> str:
        """Extract emotional/physical state"""
        # Look for feeling/state patterns
        patterns = [
            r"(覺得|感覺|feeling)\s*(.+?)(?:\s|$)",
            r"(身體|身體唔舒服|身體不舒服)\s*(.+?)(?:\s|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(2).strip()
        return text[:50]
    
    def _extract_task(self, text: str) -> str:
        """Extract delegated task"""
        # Remove common prefixes
        text = re.sub(r"^(幫我|can you|could you|帮我|麻煩你)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(得閒時|when you have time|得闲时|有機會時)", "", text, flags=re.IGNORECASE)
        text = text.strip()
        return text[:100]
    
    def _extract_event(self, text: str) -> str:
        """Extract sensitive event"""
        text = re.sub(r"^(保密|confidential|私人|private|sensitive)", "", text, flags=re.IGNORECASE)
        text = text.strip()
        return text[:100]
    
    def _get_time_anchor(self) -> str:
        """Get current time anchor string"""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M")
    
    def write_staged_item(self, classification: MessageClassification) -> str:
        """
        Write a staged item to staging.json
        Returns the item ID
        """
        import uuid
        from datetime import datetime
        
        item_id = f"staged_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        item = {
            "id": item_id,
            "created": now,
            "updated": now,
            "entity_name": classification.entity_name,
            "event_type": classification.event_type.value if classification.event_type else None,
            "context_before": classification.context_before,
            "event_core": classification.event_core,
            "followup_focus": classification.followup_focus,
            "causal_memory": classification.causal_memory,
            "confidence": classification.confidence,
        }
        
        # Load existing staging
        staging_path = self.state_dir / "staging.json"
        staging = json.loads(staging_path.read_text())
        
        # Add new item
        staging["items"].append(item)
        staging["updated"] = now
        
        # Save
        staging_path.write_text(json.dumps(staging, indent=2, ensure_ascii=False))
        
        return item_id
    
    def write_tracked_incident(self, classification) -> str:
        """
        Write a tracked incident to incidents.json
        Returns the incident ID
        
        Args:
            classification: MessageClassification object or dict with classification fields
        """
        import uuid
        from datetime import datetime
        
        incident_id = f"incident_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        # Handle both MessageClassification objects and dicts
        if isinstance(classification, dict):
            entity_name = classification.get("entity_name", "")
            event_type = classification.get("event_type")
            context_before = classification.get("context_before")
            event_core = classification.get("event_core")
            followup_focus = classification.get("followup_focus")
            causal_memory = classification.get("causal_memory", {})
            confidence = classification.get("confidence", 1.0)
        else:
            entity_name = classification.entity_name
            event_type = classification.event_type.value if classification.event_type else None
            context_before = classification.context_before
            event_core = classification.event_core
            followup_focus = classification.followup_focus
            causal_memory = classification.causal_memory
            confidence = classification.confidence
        
        incident = {
            "id": incident_id,
            "created": now,
            "updated": now,
            "entity_name": entity_name,
            "event_type": event_type,
            "context_before": context_before,
            "event_core": event_core,
            "immediate_result": None,  # To be filled when resolved
            "followup_focus": followup_focus,
            "causal_memory": causal_memory,
            "confidence": confidence,
            "status": "active",
        }
        
        # Load existing incidents
        incidents_path = self.state_dir / "incidents.json"
        incidents = json.loads(incidents_path.read_text())
        
        # Add new incident
        incidents["items"].append(incident)
        incidents["updated"] = now
        
        # Save
        incidents_path.write_text(json.dumps(incidents, indent=2, ensure_ascii=False))
        
        return incident_id
    
    def get_pending_topics(self, types: List[str] = None, limit: int = 5) -> List[Dict]:
        """
        Get pending topics for carryover
        Uses existing OCM Sup graph search if available
        """
        pending = []
        
        # Load staging items
        staging_path = self.state_dir / "staging.json"
        if staging_path.exists():
            staging = json.loads(staging_path.read_text())
            for item in staging.get("items", []):
                if types is None or item.get("event_type") in types:
                    pending.append(item)
        
        # Load active incidents
        incidents_path = self.state_dir / "incidents.json"
        if incidents_path.exists():
            incidents = json.loads(incidents_path.read_text())
            for incident in incidents.get("items", []):
                if incident.get("status") == "active":
                    if types is None or incident.get("event_type") in types:
                        pending.append(incident)
        
        # Sort by created date (newest first) and limit
        pending.sort(key=lambda x: x.get("created", ""), reverse=True)
        return pending[:limit]
    
    def update_carryover(self, turns: List[Dict], pending_topic: Optional[Dict] = None):
        """
        Update the carryover state with recent turns
        Called after each exchange to maintain context
        """
        from datetime import datetime
        
        carryover_path = self.state_dir / "carryover.json"
        carryover = {
            "turns": turns[-self.settings.get("carryover", {}).get("max_turns", 5):],
            "pending_topic": pending_topic,
            "updated": datetime.now().isoformat(),
        }
        
        carryover_path.write_text(json.dumps(carryover, indent=2, ensure_ascii=False))
    
    def get_carryover(self) -> Dict:
        """Get current carryover state for /new sessions"""
        carryover_path = self.state_dir / "carryover.json"
        if carryover_path.exists():
            return json.loads(carryover_path.read_text())
        return {"turns": [], "pending_topic": None, "updated": None}
    
    def build_runtime_context(self, is_new_session: bool = False, user_text: str = "") -> Dict:
        """
        Build runtime context for the agent
        Called before generating a reply
        """
        if not is_new_session:
            # Normal conversation - no special context needed
            return {"type": "normal", "pending_topics": []}
        
        # /new session - build carryover context
        carryover = self.get_carryover()
        pending_topics = self.get_pending_topics(limit=3)
        
        # Build context for the new session
        context = {
            "type": "new_session_carryover",
            "carryover_turns": carryover.get("turns", []),
            "pending_topic": carryover.get("pending_topic"),
            "pending_topics": pending_topics,
            "time_state": self._evaluate_time_state(),
        }
        
        return context
    
    def _evaluate_time_state(self) -> Dict:
        """
        Evaluate current time state (sleep/wake/active_day)
        Based on routine_schedule settings
        """
        from datetime import datetime
        
        schedule = self.settings.get("routine_schedule", {})
        sleep_time = schedule.get("sleep_time", "00:00")
        wake_time = schedule.get("wake_time", "08:30")
        timezone = schedule.get("timezone", "Asia/Hong_Kong")
        
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        # Parse sleep/wake times
        sleep_hour, sleep_min = map(int, sleep_time.split(":"))
        wake_hour, wake_min = map(int, wake_time.split(":"))
        
        current_hour = now.hour
        current_min = now.minute
        
        # Determine phase
        # Sleep: sleep_time to wake_time (crosses midnight)
        # Active: wake_time to sleep_time
        
        def time_to_minutes(h, m):
            return h * 60 + m
        
        current_minutes = time_to_minutes(current_hour, current_min)
        sleep_minutes = time_to_minutes(sleep_hour, sleep_min)
        wake_minutes = time_to_minutes(wake_hour, wake_min)
        
        if sleep_minutes > wake_minutes:
            # Sleep crosses midnight (e.g., 00:00 to 08:30)
            is_sleep = current_minutes >= sleep_minutes or current_minutes < wake_minutes
        else:
            # Normal case (e.g., 23:00 to 07:00)
            is_sleep = current_minutes >= sleep_minutes or current_minutes < wake_minutes
        
        phase = "sleep" if is_sleep else "active_day"
        
        return {
            "phase": phase,
            "current_time": current_time_str,
            "timezone": timezone,
            "sleep_time": sleep_time,
            "wake_time": wake_time,
        }


def main():
    """Test the state router"""
    router = StateRouter()
    
    # Test cases
    test_messages = [
        "幫我記住我哋研究緊OCM Sup融合方案",
        "記得遲啲再傾呢個",
        "我感覺有啲攰",
        "麻煩你幫我跟進這個項目",
        "呢個係私人資料，保密",
        "你好嗎？",
    ]
    
    print("=== State Router Test ===\n")
    for msg in test_messages:
        result = router.classify(msg)
        print(f"Input: {msg}")
        print(f"  Routing: {result.routing.value}")
        print(f"  Event Type: {result.event_type.value if result.event_type else 'N/A'}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Followup Focus: {result.followup_focus}")
        print()


if __name__ == "__main__":
    main()
