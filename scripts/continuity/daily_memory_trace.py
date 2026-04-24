"""
Daily Memory Traces
===================

Writes structured traces for staged and tracked items to daily memory.

Features:
1. Appends concise traces to daily memory file
2. Includes causal context (what happened before/after)
3. Auditable trail for all continuity events
4. Automatic cleanup of old traces

The trace format is designed for:
- Human readability
- Easy searching
- Future analysis
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class DailyMemoryTrace:
    """
    Writes and manages daily memory traces for continuity events.
    
    Usage:
        trace = DailyMemoryTrace(
            memory_dir="/root/.openclaw/workspace/memory"
        )
        
        # Write a trace
        trace.write(
            event_type="parked_topic",
            action="created",
            entity_name="OCM Sup 研究",
            causal_memory={...}
        )
        
        # Get today's traces
        today_traces = trace.get_today_traces()
        
        # Get traces by topic
        topic_traces = trace.get_traces_by_topic("OCM Sup")
    """
    
    def __init__(
        self,
        memory_dir: str = "/root/.openclaw/workspace/memory",
        continuity_dir: str = "/root/.openclaw/workspace/OCM-Sup/scripts/continuity"
    ):
        self.memory_dir = Path(memory_dir)
        self.continuity_dir = Path(continuity_dir)
        
        # Ensure directories exist
        self.memory_dir.mkdir(parents=True, exist_ok=True)
    
    def _today_file(self) -> Path:
        """Get today's memory file path"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.memory_dir / f"{today}.md"
    
    def _ensure_memory_file(self):
        """Ensure today's memory file exists with header"""
        today_file = self._today_file()
        
        if not today_file.exists():
            # Create with header
            header = f"# Daily Memory — {datetime.now().strftime('%Y-%m-%d')}\n\n"
            today_file.write_text(header, encoding="utf-8")
        
        return today_file
    
    def write(
        self,
        event_type: str,
        action: str,
        entity_name: str,
        topic_id: Optional[str] = None,
        causal_memory: Optional[Dict] = None,
        details: Optional[Dict] = None,
        severity: str = "info"
    ) -> Path:
        """
        Write a trace entry to daily memory.
        
        Args:
            event_type: Type of event (parked_topic, delegated_task, etc.)
            action: Action (created, resolved, updated, etc.)
            entity_name: Name of the entity/topic
            topic_id: Optional topic ID
            causal_memory: Causal memory dict
            details: Additional details
            severity: Trace severity (info, warn, error)
            
        Returns:
            Path to the updated memory file
        """
        today_file = self._ensure_memory_file()
        
        # Build trace entry
        timestamp = datetime.now().strftime("%H:%M")
        
        # Build the trace content
        lines = []
        
        # Separator
        lines.append("---")
        
        # Header with severity
        severity_emoji = {
            "info": "📝",
            "warn": "⚠️",
            "error": "❌",
            "resolved": "✅",
            "created": "🆕",
        }.get(severity, "📝")
        
        lines.append(f"**{severity_emoji} Continuity [{event_type}] — {timestamp}**")
        lines.append("")
        
        # Core info
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Action | {action} |")
        lines.append(f"| Topic | {entity_name} |")
        
        if topic_id:
            lines.append(f"| Topic ID | {topic_id} |")
        
        lines.append(f"| Event Type | {event_type} |")
        
        # Causal memory if provided
        if causal_memory:
            lines.append("")
            lines.append("**Causal Context:**")
            
            if causal_memory.get("facts"):
                facts = causal_memory.get("facts", [])
                if isinstance(facts, list):
                    for fact in facts[:3]:  # Max 3 facts
                        lines.append(f"- {fact}")
                else:
                    lines.append(f"- {facts}")
            
            if causal_memory.get("state"):
                lines.append(f"- State: {causal_memory.get('state')}")
            
            if causal_memory.get("time_anchor"):
                lines.append(f"- Time anchor: {causal_memory.get('time_anchor')}")
            
            if causal_memory.get("followup_focus_code"):
                lines.append(f"- Follow-up code: {causal_memory.get('followup_focus_code')}")
        
        # Additional details
        if details:
            lines.append("")
            lines.append("**Details:**")
            for key, value in details.items():
                if key not in ["topic_id", "causal_memory"]:  # Skip already shown
                    lines.append(f"- {key}: {value}")
        
        # Footer separator
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Append to file
        content = today_file.read_text(encoding="utf-8")
        content += "\n".join(lines)
        today_file.write_text(content, encoding="utf-8")
        
        # Also write to continuity audit file
        self._write_audit_log(event_type, action, entity_name, topic_id, causal_memory)
        
        return today_file
    
    def _write_audit_log(
        self,
        event_type: str,
        action: str,
        entity_name: str,
        topic_id: Optional[str],
        causal_memory: Optional[Dict]
    ):
        """Write to the continuity audit log"""
        audit_file = self.continuity_dir / "traces_audit.jsonl"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "event_type": event_type,
            "action": action,
            "entity_name": entity_name,
            "topic_id": topic_id,
            "causal_memory": causal_memory,
        }
        
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def get_today_traces(self, event_type: Optional[str] = None) -> List[Dict]:
        """
        Get all traces from today.
        
        Args:
            event_type: Optional filter by event type
            
        Returns:
            List of trace entries
        """
        today_file = self._today_file()
        
        if not today_file.exists():
            return []
        
        content = today_file.read_text(encoding="utf-8")
        
        # Parse traces from markdown
        traces = []
        current_trace = None
        
        for line in content.split("\n"):
            if line.startswith("**📝 Continuity") or line.startswith("**⚠️ Continuity") or line.startswith("**❌ Continuity") or line.startswith("**✅ Continuity") or line.startswith("**🆕 Continuity"):
                # Start new trace
                if current_trace:
                    traces.append(current_trace)
                
                current_trace = {
                    "raw": line,
                    "timestamp": line.split("—")[1].strip().rstrip("**") if "—" in line else None,
                    "event_type": None,
                    "action": None,
                    "entity_name": None,
                }
                
                # Extract event type from brackets
                import re
                match = re.search(r'\[(\w+)\]', line)
                if match:
                    current_trace["event_type"] = match.group(1)
            
            elif current_trace and "|" in line:
                # Parse table line
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    field = parts[1]
                    value = parts[2]
                    
                    if field == "Action":
                        current_trace["action"] = value
                    elif field == "Topic":
                        current_trace["entity_name"] = value
                    elif field == "Topic ID":
                        current_trace["topic_id"] = value
        
        # Don't forget the last trace
        if current_trace:
            traces.append(current_trace)
        
        # Filter by event type if specified
        if event_type:
            traces = [t for t in traces if t.get("event_type") == event_type]
        
        return traces
    
    def get_traces_by_topic(self, topic_query: str, limit: int = 10) -> List[Dict]:
        """
        Search traces by topic name.
        
        Args:
            topic_query: Topic name to search for
            limit: Maximum number of traces
            
        Returns:
            List of matching traces
        """
        # Search in audit log
        audit_file = self.continuity_dir / "traces_audit.jsonl"
        
        if not audit_file.exists():
            return []
        
        results = []
        
        with open(audit_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                    
                    # Search in entity name
                    if topic_query.lower() in entry.get("entity_name", "").lower():
                        results.append(entry)
                    
                    # Search in causal memory facts
                    cm = entry.get("causal_memory", {})
                    if cm:
                        facts = cm.get("facts", [])
                        for fact in facts:
                            if topic_query.lower() in str(fact).lower():
                                results.append(entry)
                                break
                
                except:
                    continue
        
        # Sort by timestamp (newest first) and limit
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]
    
    def get_weekly_summary(self) -> Dict:
        """
        Get a weekly summary of continuity events.
        
        Returns:
            Dict with summary statistics
        """
        # Get traces from last 7 days
        today = datetime.now()
        traces_by_date = {}
        
        for i in range(7):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            memory_file = self.memory_dir / f"{date_str}.md"
            
            if memory_file.exists():
                content = memory_file.read_text(encoding="utf-8")
                
                # Count traces by event type
                import re
                event_types = re.findall(r'\[(\w+_topic|\w+_task|\w+_event)\]', content)
                
                traces_by_date[date_str] = {
                    "total": len(event_types),
                    "by_type": {}
                }
                
                for et in event_types:
                    traces_by_date[date_str]["by_type"][et] = \
                        traces_by_date[date_str]["by_type"].get(et, 0) + 1
        
        # Calculate totals
        total_traces = sum(d["total"] for d in traces_by_date.values())
        
        return {
            "period": f"{(today - timedelta(days=6)).strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}",
            "total_traces": total_traces,
            "by_date": traces_by_date,
        }
    
    def cleanup_old_traces(self, days_to_keep: int = 30) -> int:
        """
        Clean up old traces from audit log.
        
        Args:
            days_to_keep: Number of days to keep
            
        Returns:
            Number of entries removed
        """
        audit_file = self.continuity_dir / "traces_audit.jsonl"
        
        if not audit_file.exists():
            return 0
        
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        # Read all entries
        with open(audit_file, "r", encoding="utf-8") as f:
            entries = [json.loads(line) for line in f if line.strip()]
        
        # Filter to keep only recent entries
        kept_entries = []
        removed = 0
        
        for entry in entries:
            try:
                entry_date = datetime.fromisoformat(entry.get("timestamp", "2000-01-01"))
                if entry_date >= cutoff:
                    kept_entries.append(entry)
                else:
                    removed += 1
            except:
                # Keep entries with invalid timestamps
                kept_entries.append(entry)
        
        # Write back
        with open(audit_file, "w", encoding="utf-8") as f:
            for entry in kept_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        return removed


def main():
    """Test the daily memory trace"""
    trace = DailyMemoryTrace()
    
    print("=== Daily Memory Trace Test ===\n")
    
    # Test 1: Write a trace
    print("--- Write Trace ---")
    path = trace.write(
        event_type="parked_topic",
        action="created",
        entity_name="OCM Sup 融合研究 Phase 2",
        topic_id="continuity_ocm_phase2_20260424",
        causal_memory={
            "facts": ["Phase 1 完成", "Phase 2 包括 Hook Lifecycle"],
            "state": "active",
            "time_anchor": "2026-04-24 14:00",
        }
    )
    print(f"Written to: {path}")
    print()
    
    # Test 2: Write another trace
    print("--- Write Another Trace ---")
    trace.write(
        event_type="delegated_task",
        action="created",
        entity_name="古洞站項目進度跟進",
        causal_memory={
            "facts": ["QS 工作相關"],
            "state": "delegated",
        },
        severity="info"
    )
    print("Written")
    print()
    
    # Test 3: Get today's traces
    print("--- Today's Traces ---")
    today_traces = trace.get_today_traces()
    print(f"Found {len(today_traces)} traces:")
    for t in today_traces:
        print(f"  - [{t.get('event_type')}] {t.get('entity_name')} ({t.get('action')})")
    print()
    
    # Test 4: Search by topic
    print("--- Search by Topic ---")
    results = trace.get_traces_by_topic("OCM Sup")
    print(f"Found {len(results)} traces for 'OCM Sup':")
    for r in results:
        print(f"  - {r.get('date')}: {r.get('entity_name')}")
    print()
    
    # Test 5: Weekly summary
    print("--- Weekly Summary ---")
    summary = trace.get_weekly_summary()
    print(f"Period: {summary['period']}")
    print(f"Total traces: {summary['total_traces']}")
    print()


if __name__ == "__main__":
    main()
