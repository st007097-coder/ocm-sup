#!/usr/bin/env python3
"""
Session Start Memory Load
OCM Sup v2.3 - Task 3 + Task 4

自動喺 session 開始時 load 相關 context，唔靠 keyword trigger。

整合 Task 4: Pre-Compression Checkpoint
- Load must_keep_facts.md (壓縮前保存的重要 facts)

Usage:
    python3 session_start_memory_load.py              # Full load
    python3 session_start_memory_load.py --quick    # Quick load (last session only)
    python3 session_start_memory_load.py --report   # Generate report
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add Triple-Stream Search to path
sys.path.insert(0, '/home/jacky/.openclaw/workspace/skills/triple-stream-search/scripts')


class SessionStartMemoryLoader:
    """
    Session 開始時自動 load 相關 context。
    
    功能：
    1. 讀取上次 session summary
    2. 讀取 recent daily memories (last 7 days)
    3. 讀取 must_keep_facts (壓縮前保存的重要 facts) [Task 4]
    4. 搵出呢期討論嘅 entities / topics
    5. 生成 context summary for injection
    """
    
    def __init__(
        self,
        memory_dir: str = "/home/jacky/.openclaw/workspace/memory",
        session_summary_dir: str = "/home/jacky/.openclaw/workspace/memory/session_summaries",
        must_keep_file: str = "/home/jacky/.openclaw/workspace/memory/must_keep_facts.md",
        wiki_path: str = "/home/jacky/.openclaw/workspace/wiki",
        days_back: int = 7,
    ):
        self.memory_dir = Path(memory_dir)
        self.session_summary_dir = Path(session_summary_dir)
        self.must_keep_file = Path(must_keep_file)
        self.wiki_path = Path(wiki_path)
        self.days_back = days_back
        
        # Create session summary dir if not exists
        self.session_summary_dir.mkdir(parents=True, exist_ok=True)
    
    def load_last_session_summary(self) -> Optional[str]:
        """Load the most recent session summary"""
        summaries = sorted(
            self.session_summary_dir.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if summaries:
            latest = summaries[0]
            return latest.read_text(encoding='utf-8')
        return None
    
    def load_must_keep_facts(self) -> Optional[str]:
        """Load must_keep_facts from pre-compression checkpoint [Task 4]"""
        if self.must_keep_file.exists():
            return self.must_keep_file.read_text(encoding='utf-8')
        return None
    
    def load_recent_daily_memories(self) -> List[Dict]:
        """Load daily memories from the last N days"""
        memories = []
        today = datetime.now()
        
        for i in range(self.days_back):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Check various possible locations for daily memory
            possible_paths = [
                self.memory_dir / f"{date_str}.md",
                self.memory_dir / date_str / "summary.md",
                self.wiki_path / "daily" / f"{date_str}.md",
            ]
            
            for path in possible_paths:
                if path.exists():
                    content = path.read_text(encoding='utf-8')
                    memories.append({
                        'date': date_str,
                        'path': str(path),
                        'content': content[:500],  # First 500 chars
                    })
                    break
        
        return memories
    
    def load_work_checkpoint(self) -> Dict:
        """Load work in progress checkpoint (P4 Enhancement)"""
        checkpoint_path = self.memory_dir / "work-in-progress.json"
        if checkpoint_path.exists():
            try:
                return json.loads(checkpoint_path.read_text(encoding='utf-8'))
            except:
                pass
        return {}
    
    def extract_key_entities(self, memories: List[Dict]) -> List[str]:
        """Extract key entities mentioned in recent memories"""
        entities = []
        
        # Load recent entity changes
        entity_changes_path = self.wiki_path / "reports" / "entity-changes.md"
        if entity_changes_path.exists():
            content = entity_changes_path.read_text(encoding='utf-8')
            # Extract entity names (simple heuristic)
            lines = content.split('\n')[:10]  # First 10 lines
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    entities.append(line.strip())
        
        return entities[:5]  # Top 5
    
    def generate_context_summary(self) -> str:
        """Generate the context summary for injection"""
        lines = []
        lines.append("## 📋 當前 Context (Session Start Auto-load)")
        lines.append("")
        
        # Must keep facts [Task 4]
        must_keep = self.load_must_keep_facts()
        if must_keep:
            lines.append("### 🔒 Must Keep Facts (Pre-Compression Checkpoint)")
            lines.append(must_keep[:500])  # First 500 chars
            lines.append("")
        
        # Work checkpoint (P4 Enhancement)
        checkpoint = self.load_work_checkpoint()
        if checkpoint:
            lines.append("### 📌 Work in Progress (Last Session)")
            lines.append(f"**Project:** {checkpoint.get('project', 'Unknown')}")
            lines.append(f"**Status:** {checkpoint.get('current_status', 'Unknown')}")
            if checkpoint.get('next_action'):
                lines.append(f"**Next:** {checkpoint.get('next_action')}")
            progress = checkpoint.get('progress_log', [])
            if progress:
                lines.append("")
                lines.append("**Recent Progress:**")
                for entry in progress[-5:]:
                    lines.append(f"- [{entry.get('time', '')}] {entry.get('action', '')} {entry.get('status', '')}")
            lines.append("")
        
        # Last session summary
        last_session = self.load_last_session_summary()
        if last_session:
            lines.append("### 🔄 上次 Session")
            lines.append(last_session[:300])  # First 300 chars
            lines.append("")
        
        # Recent daily memories
        recent = self.load_recent_daily_memories()
        if recent:
            lines.append(f"### 📅 近 {len(recent)} 日 Memory")
            for mem in recent[:3]:  # Top 3
                lines.append(f"- **{mem['date']}**: {mem['content'][:100]}...")
            lines.append("")
        
        # Key entities
        key_entities = self.extract_key_entities(recent)
        if key_entities:
            lines.append("### 🔑 近期 Entities")
            for entity in key_entities:
                lines.append(f"- {entity}")
            lines.append("")
        
        lines.append("---")
        lines.append("*呢啲係 auto-load 嘅 context，請確保你嘅回覆考慮曬呢啲資訊。*")
        
        return '\n'.join(lines)
    
    def save_session_summary(self, summary: str) -> str:
        """Save current session summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}.md"
        filepath = self.session_summary_dir / filename
        filepath.write_text(summary, encoding='utf-8')
        return str(filepath)
    
    def run(self, quick: bool = False) -> Dict:
        """Run the memory load"""
        print("🔄 Session Start Memory Load...")
        print()
        
        result = {
            'must_keep_facts': None,
            'last_session': None,
            'recent_memories': [],
            'context_summary': None,
            'ready_for_injection': False,
        }
        
        # Load must_keep_facts [Task 4]
        must_keep = self.load_must_keep_facts()
        if must_keep:
            print(f"🔒 Must Keep Facts: ✅ loaded")
            result['must_keep_facts'] = must_keep
        else:
            print("🔒 Must Keep Facts: ❌ not found")
        
        # Load last session
        last_session = self.load_last_session_summary()
        if last_session:
            print(f"✅ Last session: {last_session[:100]}...")
            result['last_session'] = last_session
        else:
            print("❌ No last session found")
        
        # Load recent memories
        if not quick:
            recent = self.load_recent_daily_memories()
            print(f"📅 Recent memories: {len(recent)} days")
            result['recent_memories'] = recent
        
        # Generate context summary
        context_summary = self.generate_context_summary()
        result['context_summary'] = context_summary
        result['ready_for_injection'] = True
        
        print()
        print("📊 Context Summary:")
        print(context_summary)
        
        return result


def main():
    parser = argparse.ArgumentParser(description='Session Start Memory Load')
    parser.add_argument('--quick', action='store_true', help='Quick load (last session only)')
    parser.add_argument('--report', action='store_true', help='Generate report only')
    
    args = parser.parse_args()
    
    loader = SessionStartMemoryLoader()
    
    if args.report:
        summary = loader.generate_context_summary()
        print(summary)
    else:
        result = loader.run(quick=args.quick)
        
        if result['ready_for_injection']:
            print()
            print("✅ Context loaded and ready for injection")
            print()
            print("To inject into current session, paste the above summary into your context.")


if __name__ == '__main__':
    main()
