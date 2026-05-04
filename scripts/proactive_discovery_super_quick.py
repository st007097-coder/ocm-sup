#!/usr/bin/env python3
"""
Proactive Knowledge Discovery - Super Quick Mode
OCM Sup v2.3 - Task 5, 6 Optimization

超快模式：直接掃描 wiki 目錄，唔需要 load Triple-Stream Search。

Usage:
    python3 proactive_discovery_super_quick.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple

WIKI_PATH = Path("/home/jacky/.openclaw/workspace/wiki")
STATE_FILE = Path("/home/jacky/.openclaw/scripts/.proactive_state.json")
DISCOVERY_LOG = Path("/home/jacky/.openclaw/scripts/.proactive_discovery_log.json")


class SuperQuickDiscovery:
    """
    超快版本：直接掃描 wiki 目錄，唔需要 load Triple-Stream Search。
    
    速度：~1-2 秒完成（vs 275+ 秒原版）
    """
    
    def __init__(self):
        self.state_file = STATE_FILE
        self.previous_entities: Set[str] = set()
        self.load_state()
    
    def load_state(self):
        """Load previous entity state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.previous_entities = set(data.get('entities', []))
                    print(f"📂 Loaded previous state: {len(self.previous_entities)} entities")
            except Exception as e:
                print(f"⚠️ Failed to load state: {e}")
    
    def scan_entities(self) -> Tuple[List[str], List[str]]:
        """Scan wiki path for entity files"""
        current_entities = set()
        
        # Scan knowledge/ai-agent/entities/
        entities_dir = WIKI_PATH / "knowledge" / "ai-agent" / "entities"
        if entities_dir.exists():
            for f in entities_dir.glob("*.md"):
                entity_id = f.stem  # filename without extension
                current_entities.add(entity_id)
        
        # Also scan knowledge/concepts/
        concepts_dir = WIKI_PATH / "knowledge" / "concepts"
        if concepts_dir.exists():
            for f in concepts_dir.glob("*.md"):
                entity_id = f.stem
                current_entities.add(entity_id)
        
        # Also scan knowledge/systems/
        systems_dir = WIKI_PATH / "knowledge" / "systems"
        if systems_dir.exists():
            for f in systems_dir.glob("*.md"):
                entity_id = f.stem
                current_entities.add(entity_id)
        
        new_entities = current_entities - self.previous_entities
        removed_entities = self.previous_entities - current_entities
        
        return list(new_entities), list(removed_entities)
    
    def save_state(self, entities: Set[str]):
        """Save current entity state"""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'entities': list(entities),
                'last_updated': datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved state: {len(entities)} entities")
    
    def log_discovery(self, new_entities: List[str], removed_entities: List[str]):
        """Log discovery results"""
        log_file = DISCOVERY_LOG
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        existing = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except:
                pass
        
        existing.append({
            'timestamp': datetime.now().isoformat(),
            'new_entities': new_entities,
            'removed_entities': removed_entities,
        })
        
        # Keep only last 100 entries
        existing = existing[-100:]
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    
    def discover(self) -> Dict:
        """Run super quick discovery"""
        print("🔍 Super Quick Discovery starting...")
        print(f"   Time: {datetime.now().isoformat()}")
        print()
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'new_entities': [],
            'removed_entities': [],
        }
        
        # Scan for entity changes
        print("📊 Scanning for entity changes...")
        new_entities, removed_entities = self.scan_entities()
        
        if new_entities:
            print(f"   🆕 New entities: {len(new_entities)}")
            for name in new_entities[:10]:
                print(f"      - {name}")
            if len(new_entities) > 10:
                print(f"      ... and {len(new_entities) - 10} more")
        else:
            print("   ✅ No new entities")
        
        if removed_entities:
            print(f"   ❌ Removed entities: {len(removed_entities)}")
        else:
            print("   ✅ No removed entities")
        
        # Save state
        all_entities = self.previous_entities | set(new_entities)
        self.save_state(all_entities)
        
        # Log discovery
        self.log_discovery(new_entities, removed_entities)
        
        results['new_entities'] = new_entities
        results['removed_entities'] = removed_entities
        
        print()
        print("✅ Discovery completed!")
        
        return results


def main():
    discovery = SuperQuickDiscovery()
    results = discovery.discover()
    
    print()
    print("📋 Results:")
    print(f"   New entities: {len(results['new_entities'])}")
    print(f"   Removed entities: {len(results['removed_entities'])}")


if __name__ == '__main__':
    main()