#!/usr/bin/env python3
"""
Proactive Knowledge Discovery
OCM Sup 7-Dir 6: Automatically discovers new knowledge and suggests relationship updates

Usage:
    python3 proactive_discovery.py                    # Full scan
    python3 proactive_discovery.py --quick          # Quick scan
    python3 proactive_discovery.py --watch          # Continuous monitoring
    python3 proactive_discovery.py --report        # Generate report
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

sys.path.insert(0, '/root/.openclaw/workspace/skills/triple-stream-search/scripts')

from triple_stream_search import TripleStreamSearch

class ProactiveDiscovery:
    """
    Proactively discovers new knowledge and suggests relationship updates.
    
    Responsibilities:
    1. Detect new entities in wiki
    2. Find relationships between new and existing entities
    3. Detect entity updates (new content)
    4. Generate discovery reports
    """
    
    def __init__(self, wiki_path: str = "/root/.openclaw/workspace/wiki"):
        self.wiki_path = Path(wiki_path)
        self.search = TripleStreamSearch(wiki_path=wiki_path)
        self.graph = self.search.graph_channel
        
        # Track discovered knowledge
        self.discoveries: List[Dict] = []
        self.suggested_updates: List[Dict] = []
        
        # Load previous state
        self.state_file = Path("/root/.openclaw/scripts/.proactive_state.json")
        self.previous_entities: Set[str] = set()
        self.load_state()
    
    def load_state(self):
        """Load previous entity state for comparison"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.previous_entities = set(data.get('entities', []))
                    print(f"📂 Loaded previous state: {len(self.previous_entities)} entities")
            except:
                pass
    
    def save_state(self):
        """Save current entity state"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        current_entities = set(self.graph.nodes.keys())
        
        with open(self.state_file, 'w') as f:
            json.dump({
                'entities': list(current_entities),
                'last_updated': datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Saved state: {len(current_entities)} entities")
    
    def scan_new_entities(self) -> Tuple[List[str], List[str]]:
        """Scan for new and removed entities since last check"""
        current_entities = set(self.graph.nodes.keys())
        
        new_entities = current_entities - self.previous_entities
        removed_entities = self.previous_entities - current_entities
        
        return list(new_entities), list(removed_entities)
    
    def analyze_entity_content(self, entity_name: str) -> Dict:
        """Analyze entity content to find related entities"""
        node = self.graph.nodes.get(entity_name)
        if not node:
            return {}
        
        # Get content snippet
        content = getattr(node, 'content_snippet', '') or ''
        
        # Find related entities mentioned in content
        related = []
        for other_id, other_node in self.graph.nodes.items():
            if other_id == entity_name:
                continue
            # Check if entity name appears in content
            if other_node.name.lower() in content.lower():
                related.append({
                    'name': other_node.name,
                    'id': other_id,
                    'type': 'name_mention',
                })
        
        # Check for keyword-based relationships
        keywords = {
            'openclaw': ['OpenClaw', 'openclaw'],
            'ocm_sup': ['OCM Sup', 'ocm-sup'],
            '期哥': ['期哥', 'jacky'],
            '古洞站': ['古洞站', 'Kwu Tung'],
            '阿星': ['阿星', 'Ah Sing'],
        }
        
        for category, terms in keywords.items():
            if any(term.lower() in content.lower() for term in terms):
                if category == 'ocm_sup':
                    related.append({
                        'name': 'OCM Sup',
                        'id': 'ocm-sup',
                        'type': 'keyword_match',
                    })
        
        return {
            'entity_name': entity_name,
            'entity_type': node.entity_type,
            'related': related,
            'content_length': len(content),
        }
    
    def _infer_relationship_type(self, from_entity: str, to_entity: str, context: str) -> Tuple[str, float]:
        """
        Infer the relationship type between two entities based on their types and context.
        Enhanced with:
        - Multi-factor confidence scoring
        - Inverse relationship inference
        - Learning from historical patterns
        Returns (relationship_type, confidence)
        """
        from_node = self.graph.nodes.get(from_entity)
        to_node = self.graph.nodes.get(to_entity)
        
        if not from_node or not to_node:
            return 'related_to', 0.3
        
        from_type = from_node.entity_type.lower()
        to_type = to_node.entity_type.lower()
        
        context_lower = context.lower()
        
        # Rule-based relationship inference
        rules = [
            # Person-related rules
            ({'person'}, {'project', 'entity'}, [
                ('works_on', 0.9, ['工作', '項目', 'project', 'responsible', '任職']),
                ('manages', 0.8, ['管理', '負責', 'manage', 'lead', '主管']),
                ('created_by', 0.7, ['創建', '建立', 'created', 'built']),
            ]),
            ({'person'}, {'technology', 'system', 'concept'}, [
                ('uses', 0.8, ['使用', 'uses', 'using', 'employ', '用']),
                ('created_by', 0.7, ['創建', '開發', 'created', 'developed']),
                ('manages', 0.6, ['管理', '配置', 'manage', 'configured']),
            ]),
            # Project-related rules
            ({'project'}, {'person'}, [
                ('involves', 0.8, ['涉及', '包含', 'involves', 'includes', 'team']),
                ('serves', 0.7, ['服務', '客戶', 'serves', 'client']),
            ]),
            ({'project'}, {'technology', 'system'}, [
                ('uses', 0.8, ['使用', '採用', 'uses', 'using', 'adopted', '使用']),
                ('part_of', 0.7, ['包含', '整合', 'part of', 'integrated']),
            ]),
            ({'project'}, {'concept'}, [
                ('implements', 0.8, ['實現', '實作', 'implements']),
                ('follows', 0.6, ['遵循', 'follows', 'based on']),
            ]),
            # System/Technology rules
            ({'system', 'technology'}, {'system', 'technology'}, [
                ('integrates_with', 0.8, ['整合', '集成', 'integrate', 'integrated with', '對接']),
                ('powers', 0.7, ['驅動', 'powers', 'enables', '支持']),
                ('depends_on', 0.6, ['依賴', 'depends on', 'requires', '需要']),
            ]),
            ({'system', 'technology'}, {'concept'}, [
                ('implements', 0.8, ['實現', 'implements', '執行']),
                ('provides', 0.7, ['提供', 'provides']),
            ]),
            # Inverse relationship inference for known patterns
            ({'project', 'system'}, {'person'}, [
                ('managed_by', 0.85, ['管理', '負責人', 'managed by', 'led by']),
            ]),
            # General fallback
            ({'entity'}, {'entity'}, [
                ('related_to', 0.5, []),
                ('related_to', 0.4, []),
            ]),
        ]
        
        base_confidence = 0.3
        matched_rule = None
        
        # Try to find matching rule
        for type_set, target_types, type_choices in rules:
            if from_type in type_set and to_type in target_types:
                for rel_type, base_conf, keywords in type_choices:
                    # Check if any keyword appears in context
                    if not keywords or any(kw.lower() in context_lower for kw in keywords):
                        matched_rule = (rel_type, base_conf)
                        break
                if matched_rule:
                    break
        
        if matched_rule:
            rel_type, base_confidence = matched_rule
        else:
            rel_type = 'related_to'
        
        # Multi-factor confidence boosting
        confidence_boost = 0.0
        
        # Boost 1: Keyword density in context
        if context:
            word_count = len(context.split())
            name_mentions = 0
            for word in [from_node.name, to_node.name]:
                name_mentions += context_lower.count(word.lower())
            keyword_density = name_mentions / max(word_count, 1)
            confidence_boost += min(keyword_density * 2, 0.2)  # Up to +0.2
        
        # Boost 2: Historical pattern matching (learned from previous suggestions)
        learned_confidence = self._get_learned_confidence(from_type, to_type, rel_type)
        confidence_boost += learned_confidence * 0.15  # Up to +0.15
        
        # Boost 3: Entity type compatibility score
        type_compatibility = self._get_type_compatibility_score(from_type, to_type)
        confidence_boost += type_compatibility * 0.1  # Up to +0.1
        
        final_confidence = min(base_confidence + confidence_boost, 0.95)
        
        return rel_type, final_confidence
    
    def _get_learned_confidence(self, from_type: str, to_type: str, rel_type: str) -> float:
        """Get learned confidence from previous suggestions"""
        learning_file = Path("/root/.openclaw/scripts/.relationship_learning.json")
        if not learning_file.exists():
            return 0.0
        
        try:
            with open(learning_file, 'r') as f:
                learning = json.load(f)
            
            key = f"{from_type}:{to_type}:{rel_type}"
            count = learning.get('accepted', {}).get(key, 0)
            total = learning.get('total', 0)
            
            if total > 0:
                return count / total
        except:
            pass
        
        return 0.0
    
    def _get_type_compatibility_score(self, from_type: str, to_type: str) -> float:
        """Get compatibility score between entity types"""
        compatibility_matrix = {
            ('person', 'project'): 0.9,
            ('person', 'system'): 0.7,
            ('person', 'concept'): 0.6,
            ('project', 'person'): 0.8,
            ('project', 'system'): 0.7,
            ('project', 'concept'): 0.6,
            ('system', 'system'): 0.5,
            ('system', 'person'): 0.4,
            ('system', 'project'): 0.5,
            ('document_title', 'entity'): 0.3,
            ('entity', 'entity'): 0.2,
        }
        
        return compatibility_matrix.get((from_type, to_type), 0.1)
    
    def record_suggestion_outcome(self, suggestion: Dict, accepted: bool):
        """Record whether a suggestion was accepted or rejected for learning"""
        learning_file = Path("/root/.openclaw/scripts/.relationship_learning.json")
        learning = {'accepted': {}, 'rejected': {}, 'total': 0}
        
        if learning_file.exists():
            try:
                with open(learning_file, 'r') as f:
                    learning = json.load(f)
            except:
                pass
        
        key = f"{suggestion.get('from_type', 'entity')}:{suggestion.get('to_type', 'entity')}:{suggestion['relationship_type']}"
        
        if accepted:
            learning['accepted'][key] = learning['accepted'].get(key, 0) + 1
        else:
            learning['rejected'][key] = learning['rejected'].get(key, 0) + 1
        
        learning['total'] += 1
        
        with open(learning_file, 'w') as f:
            json.dump(learning, f, indent=2)
    
    def _get_inverse_relationship(self, rel_type: str) -> str:
        """Get the inverse relationship type"""
        inverse_map = {
            'works_on': 'has_worker',
            'uses': 'used_by',
            'involves': 'involved_in',
            'manages': 'managed_by',
            'created_by': 'creates',
            'part_of': 'contains',
            'implements': 'implemented_by',
            'integrates_with': 'integrates_with',  # symmetric
            'powers': 'powered_by',
            'depends_on': 'is_dependency_of',
            'serves': 'served_by',
            'related_to': 'related_to',  # symmetric
            'related_to': 'related_to',
        }
        return inverse_map.get(rel_type, 'related_to')
    
    def find_relationship_suggestions(self) -> List[Dict]:
        """Find potential new relationships based on content analysis"""
        suggestions = []
        
        for entity_id, node in self.graph.nodes.items():
            analysis = self.analyze_entity_content(entity_id)
            
            # Check existing relationships (both directions)
            existing_relationships = set()
            for rel in node.relationships:
                existing_relationships.add(rel.get('target', ''))
            
            # Also check reverse relationships
            for other_id, other_node in self.graph.nodes.items():
                for rel in other_node.relationships:
                    if rel.get('target', '') == entity_id:
                        existing_relationships.add(other_id)
            
            # Find suggested relationships
            for related in analysis.get('related', []):
                if related['id'] not in existing_relationships and related['id'] != entity_id:
                    # Get content for context
                    content = getattr(node, 'content_snippet', '') or ''
                    
                    # Infer relationship type intelligently
                    rel_type, confidence = self._infer_relationship_type(
                        entity_id, related['id'], content
                    )
                    
                    suggestions.append({
                        'from_entity': node.name,
                        'from_id': entity_id,
                        'to_entity': related['name'],
                        'to_id': related['id'],
                        'relationship_type': rel_type,
                        'reason': f"{related['type']} detected, inferred as {rel_type}",
                        'confidence': confidence,
                        'from_type': node.entity_type,
                        'to_type': self.graph.nodes.get(related['id']).entity_type if self.graph.nodes.get(related['id']) else 'unknown',
                    })
        
        return suggestions
    
    def detect_entity_updates(self) -> List[Dict]:
        """Detect entities that may have been updated"""
        updates = []
        
        # Check for entities with recent file modifications
        for entity_id, node in self.graph.nodes.items():
            path = self.wiki_path / node.path
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime > datetime.now() - timedelta(days=1):
                    updates.append({
                        'entity_name': node.name,
                        'entity_id': entity_id,
                        'modified': mtime.isoformat(),
                        'type': 'recently_modified',
                    })
        
        return updates
    
    def discover(self, quick: bool = False) -> Dict:
        """Run full or quick discovery"""
        print("🔍 Running Proactive Discovery...")
        print(f"   Time: {datetime.now().isoformat()}")
        print()
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'new_entities': [],
            'removed_entities': [],
            'relationship_suggestions': [],
            'entity_updates': [],
            'discoveries': [],
        }
        
        # Scan for new entities
        print("📊 Scanning for entity changes...")
        new_entities, removed_entities = self.scan_new_entities()
        
        if new_entities:
            print(f"   🆕 New entities: {len(new_entities)}")
            results['new_entities'] = new_entities
            for name in new_entities[:10]:
                print(f"      - {name}")
            if len(new_entities) > 10:
                print(f"      ... and {len(new_entities) - 10} more")
        else:
            print("   ✅ No new entities")
        
        if removed_entities:
            print(f"   ❌ Removed entities: {len(removed_entities)}")
            results['removed_entities'] = removed_entities
        else:
            print("   ✅ No removed entities")
        
        print()
        
        # Find relationship suggestions (unless quick mode)
        if not quick:
            print("🔗 Finding relationship suggestions...")
            suggestions = self.find_relationship_suggestions()
            
            # Filter out duplicates and existing relationships
            unique_suggestions = []
            seen = set()
            for s in suggestions:
                key = (s['from_id'], s['to_id'])
                if key not in seen and s['from_id'] != s['to_id']:
                    seen.add(key)
                    unique_suggestions.append(s)
            
            if unique_suggestions:
                print(f"   💡 Found {len(unique_suggestions)} relationship suggestions")
                results['relationship_suggestions'] = unique_suggestions[:10]
                for s in unique_suggestions[:5]:
                    print(f"      - {s['from_entity']} → {s['to_entity']} ({s['reason']})")
            else:
                print("   ✅ No new relationship suggestions")
            
            print()
        
        # Detect entity updates
        print("📝 Checking for entity updates...")
        updates = self.detect_entity_updates()
        
        if updates:
            print(f"   🔄 Recently modified: {len(updates)}")
            results['entity_updates'] = updates
        else:
            print("   ✅ No recent updates")
        
        # Save state
        print()
        self.save_state()
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a human-readable report"""
        lines = [
            "# Proactive Discovery Report",
            f"Generated: {results['timestamp']}",
            "",
            "## Summary",
            "",
            f"- New entities discovered: {len(results['new_entities'])}",
            f"- Relationship suggestions: {len(results.get('relationship_suggestions', []))}",
            f"- Entity updates: {len(results.get('entity_updates', []))}",
            "",
        ]
        
        if results['new_entities']:
            lines.append("## New Entities")
            lines.append("")
            for name in results['new_entities']:
                lines.append(f"- {name}")
            lines.append("")
        
        if results.get('relationship_suggestions'):
            lines.append("## Relationship Suggestions")
            lines.append("")
            for s in results['relationship_suggestions'][:10]:
                lines.append(f"- **{s['from_entity']}** → **{s['to_entity']}**")
                lines.append(f"  - Reason: {s['reason']}")
                lines.append(f"  - Confidence: {s['confidence']:.0%}")
                lines.append("")
        
        return "\n".join(lines)
    
    def apply_suggestions(self, suggestions: List[Dict]) -> int:
        """Apply relationship suggestions to entity files"""
        applied = 0
        
        for suggestion in suggestions:
            entity_path = self.wiki_path / self.graph.nodes[suggestion['from_id']].path
            
            try:
                content = entity_path.read_text(encoding='utf-8')
                
                # Check if relationship already exists
                if f"target: {suggestion['to_id']}" in content:
                    print(f"   ⏭️  Skipped (already exists): {suggestion['from_entity']} → {suggestion['to_entity']}")
                    continue
                
                # Add relationship to frontmatter
                new_rel = f"""  - direction: outgoing
    target: {suggestion['to_id']}
    type: {suggestion['relationship_type']}
"""
                
                # Find the relationships section and add
                if 'relationships:' in content:
                    content = content.replace(
                        'relationships:',
                        f'relationships:\n{new_rel}'
                    )
                else:
                    # Add relationships section after frontmatter
                    lines = content.split('\n')
                    new_lines = []
                    for i, line in enumerate(lines):
                        new_lines.append(line)
                        if line.strip() == '---' and i > 0:
                            new_lines.append(new_rel)
                    content = '\n'.join(new_lines)
                
                entity_path.write_text(content, encoding='utf-8')
                print(f"   ✅ Applied: {suggestion['from_entity']} → {suggestion['to_entity']}")
                applied += 1
                
            except Exception as e:
                print(f"   ❌ Error updating {suggestion['from_entity']}: {e}")
        
        return applied

def main():
    parser = argparse.ArgumentParser(description='Proactive Knowledge Discovery')
    parser.add_argument('--quick', action='store_true', help='Quick scan (skip relationship analysis)')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--report', action='store_true', help='Generate report')
    parser.add_argument('--apply', action='store_true', help='Apply relationship suggestions')
    parser.add_argument('--interval', type=int, default=60, help='Watch interval in seconds')
    
    args = parser.parse_args()
    
    discovery = ProactiveDiscovery()
    
    if args.watch:
        print("👀 Starting continuous monitoring...")
        print("   Press Ctrl+C to stop")
        try:
            while True:
                results = discovery.discover(quick=args.quick)
                print(f"\n💤 Sleeping for {args.interval} seconds...")
                import time
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n👋 Stopped monitoring")
    
    elif args.report:
        results = discovery.discover(quick=args.quick)
        report = discovery.generate_report(results)
        print("\n" + report)
        
        # Save report
        report_path = Path("/root/.openclaw/scripts/proactive_discovery_report.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding='utf-8')
        print(f"\n📄 Report saved to: {report_path}")
    
    elif args.apply:
        print("🔧 Applying relationship suggestions...")
        results = discovery.discover(quick=args.quick)
        suggestions = results.get('relationship_suggestions', [])
        
        if not suggestions:
            print("   No suggestions to apply")
        else:
            applied = discovery.apply_suggestions(suggestions)
            print(f"\n✅ Applied {applied} relationship suggestions")
            
            # Reload and verify
            print("\n🔄 Reloading graph to verify...")
            discovery = ProactiveDiscovery()
            print(f"   Graph now has {len(discovery.graph.nodes)} nodes and {len(discovery.graph.edges)} edges")
    
    else:
        results = discovery.discover(quick=args.quick)
        
        # Print summary
        print()
        print("📊 Discovery Summary:")
        print(f"   New entities: {len(results['new_entities'])}")
        print(f"   Removed entities: {len(results['removed_entities'])}")
        print(f"   Relationship suggestions: {len(results.get('relationship_suggestions', []))}")
        print(f"   Entity updates: {len(results.get('entity_updates', []))}")

if __name__ == '__main__':
    main()