"""
Frontstage Guard
================

Prevents internal continuity logic from leaking into frontstage conversation.

Key protections:
1. Sanitize follow-up messages (remove internal references)
2. Block system-level jargon from appearing in user-facing text
3. Ensure natural conversational tone
4. Don't mention hook IDs, internal states, or implementation details

The guard sits between the internal continuity layer and the frontstage output.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class FrontstageGuard:
    """
    Guards against internal continuity logic leaking into frontstage.
    
    Usage:
        guard = FrontstageGuard()
        
        # Before sending a message
        safe_message = guard.sanitize(followup_message)
        
        # Check if message is safe
        is_safe = guard.is_safe(message)
        
        # Get guard statistics
        stats = guard.get_stats()
    """
    
    # Internal jargon patterns to block
    BLOCKED_PATTERNS = [
        # Hook/Incident IDs
        r"hook_[a-f0-9]{8}",
        r"incident_[a-f0-9]{8}",
        r"staged_[a-f0-9]{8}",
        
        # Internal status names
        r"\b(HookStatus|IncidentStatus|HookLifecycle)\b",
        r"\b(HookStatus\.)?(ACTIVE|DUE|DISPATCHED|PARKED|CLOSED)\b",
        
        # Internal file references
        r"(staging\.json|incidents\.json|hooks\.json)",
        r"(carryover\.json|continuity_state)",
        
        # System-level jargon
        r"\bcausal_memory\b",
        r"\brouting_type\b",
        r"\bfrontstage_guard\b",
        r"\bevent_chain\b",
        r"\bdispatch_count\b",
        r"\bcooldown_until\b",
        
        # Confusing technical terms
        r"\bTTL\b",
        r"\bparked_topic\b",
        r"\bwatchful_state\b",
        r"\bdelegated_task\b",
        r"\bsensitive_event\b",
        
        # Internal timestamps in raw form
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+",
        
        # Debug-style messages
        r"\[DEBUG\]",
        r"\[INTERNAL\]",
        r"\[SYSTEM\]",
    ]
    
    # Replace blocked patterns with cleaner alternatives
    REPLACEMENTS = {
        r"hook_[a-f0-9]{8}": "呢個跟進事項",
        r"incident_[a-f0-9]{8}": "呢個跟進事項",
        r"staged_[a-f0-9]{8}": "呢個記錄",
        r"\(上次傾呢個係 .+\)": "",  # Remove time anchor references
    }
    
    def __init__(
        self,
        state_dir: str = "/root/.openclaw/workspace/OCM-Sup/scripts/continuity"
    ):
        self.state_dir = Path(state_dir)
        
        # Initialize log
        self._init_log()
    
    def _init_log(self):
        """Initialize the guard log"""
        log_path = self.state_dir / "frontstage_guard_log.jsonl"
        if not log_path.exists():
            log_path.write_text("")
    
    def sanitize(self, message: str) -> str:
        """
        Sanitize a message for frontstage.
        
        Removes/changes:
        - Internal IDs (hook_xxx, incident_xxx)
        - System jargon
        - Raw timestamps
        - Technical implementation details
        
        Args:
            message: The potentially unsafe message
            
        Returns:
            The sanitized, frontstage-safe message
        """
        if not message:
            return message
        
        original = message
        
        # Apply replacements first
        for pattern, replacement in self.REPLACEMENTS.items():
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        
        # Block remaining patterns
        for pattern in self.BLOCKED_PATTERNS:
            message = re.sub(pattern, "[已過濾]", message, flags=re.IGNORECASE)
        
        # Clean up double spaces
        message = re.sub(r"\s+", " ", message)
        
        # Clean up "已過濾" artifacts
        message = re.sub(r"\[已過濾\]\s*\[已過濾\]", "已過濾", message)
        message = re.sub(r"^\s*\[已過濾\]\s*", "", message)
        message = re.sub(r"\s*\[已過濾\]\s*$", "", message)
        
        # If message is too sanitized (empty or just noise), return None
        if len(message.strip()) < 5:
            return None
        
        # Log the sanitization
        if message != original:
            self._log_sanitization(original, message)
        
        return message.strip()
    
    def _log_sanitization(self, original: str, sanitized: str):
        """Log a sanitization event"""
        log_path = self.state_dir / "frontstage_guard_log.jsonl"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "original_length": len(original),
            "sanitized_length": len(sanitized),
            "original_preview": original[:100],
            "sanitized_preview": sanitized[:100],
        }
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def is_safe(self, message: str) -> bool:
        """
        Check if a message is safe for frontstage.
        
        Args:
            message: The message to check
            
        Returns:
            True if safe, False if it contains internal content
        """
        if not message:
            return True
        
        # Check for blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return False
        
        # Check for raw timestamps
        if re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", message):
            return False
        
        # Check for hook/incident IDs
        if re.search(r"hook_[a-f0-9]{8}", message, re.IGNORECASE):
            return False
        if re.search(r"incident_[a-f0-9]{8}", message, re.IGNORECASE):
            return False
        
        return True
    
    def get_stats(self) -> Dict:
        """
        Get guard statistics.
        
        Returns:
            Dict with sanitization stats
        """
        log_path = self.state_dir / "frontstage_guard_log.jsonl"
        
        if not log_path.exists():
            return {"total_sanitizations": 0}
        
        try:
            lines = log_path.read_text().strip().split("\n")
            entries = [json.loads(line) for line in lines if line.strip()]
            
            today = datetime.now().date()
            today_entries = [
                e for e in entries
                if datetime.fromisoformat(e["timestamp"]).date() == today
            ]
            
            return {
                "total_sanitizations": len(entries),
                "today_sanitizations": len(today_entries),
                "log_file_size": log_path.stat().st_size if log_path.exists() else 0,
            }
        except:
            return {"error": "Could not read log"}
    
    def build_guard_context(self) -> str:
        """
        Build a guard context string for the agent prompt.
        
        This tells the agent what NOT to say in frontstage.
        
        Returns:
            A string with guard guidelines
        """
        return """
## Frontstage Guard Guidelines

當你生成主動關心或跟進訊息時，請注意：

1. **唔好提** 內部狀態名稱（如 hook、incident、staged）
2. **唔好提** ID（如 hook_xxx, incident_xxx）
3. **唔好提** 內部文件名稱（如 staging.json, incidents.json）
4. **唔好提** 技術術語（如 causal_memory、dispatch_count）
5. **用自然語言** 表达關心（如「記得你之前提到...」）
6. **移除時間戳**（如 2026-04-24T14:00:00）
7. **保持對話風格** — 唔好變成系統通知

例子：
- ❌ 唔好話：「你之前 park 咗 hook_123abc 呢個 topic」
- ✅ 應該話：「你之前提到想討論 OCM Sup 融合，仲想繼續傾嗎？」

記住：你係阿星，唔係系統管理員。用自然、關心嘅口吻。
"""


def main():
    """Test the frontstage guard"""
    guard = FrontstageGuard()
    
    print("=== Frontstage Guard Test ===\n")
    
    # Test cases
    test_messages = [
        "想提醒你之前交代嘅任務：繼續分析融合方案（上次傾呢個係 2026-04-24T14:00:00.123456）",
        "你之前提到 hook_12345678，想繼續傾嗎？",
        "留意到你之前提到病情」，情況點樣？",
        "關於 incident_abcdefgh 呢個跟進事項",
        "你之前記低咗嘅嘢幾時搞？",
        "✅ 正常自然嘅跟進：你之前話想研究 OCM Sup 融合，準備好繼續未？",
    ]
    
    print("Testing sanitization:\n")
    for msg in test_messages:
        is_safe = guard.is_safe(msg)
        sanitized = guard.sanitize(msg) if not is_safe else msg
        
        print(f"Original: {msg[:60]}...")
        print(f"Is safe: {is_safe}")
        if sanitized:
            print(f"Sanitized: {sanitized[:60]}...")
        print()
    
    # Test stats
    print("--- Guard Stats ---")
    stats = guard.get_stats()
    print(f"Stats: {stats}")
    print()
    
    # Test guard context
    print("--- Guard Context ---")
    context = guard.build_guard_context()
    print(context[:500])


if __name__ == "__main__":
    main()
