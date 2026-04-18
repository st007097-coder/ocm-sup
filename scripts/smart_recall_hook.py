#!/usr/bin/env python3
"""
Smart Memory Recall Hook
Integrates Triple-Stream Search with OCM Sup Memory System

OCM Sup 7-Dir 5: Smart Memory Recall
"""

import os
import sys
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import time

# Add Triple-Stream Search to path
sys.path.insert(0, '/root/.openclaw/workspace/skills/triple-stream-search/scripts')

from triple_stream_search import TripleStreamSearch

class SmartRecallHook:
    """
    Hooks Triple-Stream Search into OCM Sup's memory recall system.
    
    Responsibilities:
    1. Monitor memory access patterns
    2. Trigger Triple-Stream Search when relevant queries are detected
    3. Inject relevant results into context
    4. Track recall statistics for optimization
    
    Usage:
        hook = SmartRecallHook()
        results = hook.recall("古洞站", context=current_context)
        if results:
            inject_into_context(results)
    """
    
    def __init__(
        self,
        wiki_path: str = "/root/.openclaw/workspace/wiki",
        memory_dir: str = "/root/.openclaw/workspace/memory",
        max_results: int = 5,
        token_budget: int = 2000,
    ):
        self.wiki_path = wiki_path
        self.memory_dir = memory_dir
        self.max_results = max_results
        self.token_budget = token_budget
        
        # Initialize Triple-Stream Search
        self.search = TripleStreamSearch(wiki_path=wiki_path)
        
        # Track access patterns
        self.access_patterns: Dict[str, int] = defaultdict(int)
        self.recent_recalls: List[Dict] = []
        
        # Load patterns from disk
        self._load_patterns()
    
    def _load_patterns(self):
        """Load cached access patterns"""
        cache_path = Path("/root/.openclaw/scripts/.recall_patterns.json")
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    self.access_patterns = defaultdict(int, data.get('patterns', {}))
            except:
                pass
    
    def _save_patterns(self):
        """Save access patterns to disk"""
        cache_path = Path("/root/.openclaw/scripts/.recall_patterns.json")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cache_path, 'w') as f:
            json.dump({
                'patterns': dict(self.access_patterns),
                'last_updated': datetime.now().isoformat(),
            }, f, indent=2)
    
    def should_trigger(self, query: str, context: Optional[Dict] = None) -> bool:
        """
        Determine if a query should trigger Triple-Stream Search.
        
        Args:
            query: The user's query
            context: Optional context (recent messages, current topic, etc.)
        
        Returns:
            True if should trigger, False otherwise
        """
        query_lower = query.lower()
        
        # High priority triggers
        high_priority = [
            'search', 'find', 'locate', '搵', 'search', '知識',
            '古洞站', '期哥', '阿星', 'OCM', 'Sup', 'sup',
            'project', '項目', 'entity', 'graph',
            'ocm', 'openclaw', 'triple', 'stream',
            'knowledge', 'recall', 'remember',
        ]
        
        for trigger in high_priority:
            if trigger in query_lower:
                self.access_patterns[trigger] += 1
                return True
        
        # Check if query relates to known entities
        for entity_name in self.search.graph_channel.nodes.keys():
            if entity_name.lower() in query_lower:
                self.access_patterns[entity_name] += 1
                return True
        
        # Check context hints
        if context:
            topic = context.get('topic', '')
            if topic and topic.lower() in query_lower:
                return True
        
        # Frequency-based trigger (hot topics)
        hot_topics = [k for k, v in self.access_patterns.items() if v >= 3]
        for topic in hot_topics:
            if topic.lower() in query_lower:
                return True
        
        return False
    
    def recall(
        self,
        query: str,
        context: Optional[Dict] = None,
        source_filter: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Perform smart memory recall using Triple-Stream Search.
        
        Args:
            query: The search query
            context: Optional context for better results
            source_filter: Filter by sources (bm25, vector, graph)
        
        Returns:
            List of search results with metadata
        """
        start_time = time.time()
        
        # Use Triple-Stream Search
        results = self.search.search(query, top_k=self.max_results)
        
        # Filter by source if specified
        if source_filter:
            results = [r for r in results if any(s in source_filter for s in r['sources'])]
        
        # Calculate token budget usage
        total_tokens = sum(len(r['title']) + len(r['path']) for r in results)
        
        # Record recall
        recall_record = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'results_count': len(results),
            'tokens_used': total_tokens,
            'sources': list(set(sum([r['sources'] for r in results], []))),
            'latency_ms': int((time.time() - start_time) * 1000),
        }
        
        self.recent_recalls.append(recall_record)
        if len(self.recent_recalls) > 100:
            self.recent_recalls = self.recent_recalls[-100:]
        
        return results
    
    def recall_daily_memory(self, date: Optional[str] = None, query: Optional[str] = None) -> List[Dict]:
        """
        Recall from daily memory files (episodic layer).
        
        This uses a simpler BM25 search on daily memory files.
        
        Args:
            date: Optional date filter (YYYY-MM-DD format)
            query: Optional query to filter memory
        
        Returns:
            List of memory entries
        """
        memory_path = Path(self.memory_dir)
        
        if not memory_path.exists():
            return []
        
        results = []
        
        # List daily memory files
        if date:
            # Specific date
            file_path = memory_path / f"{date}.md"
            if file_path.exists():
                results.append({
                    'type': 'daily_memory',
                    'date': date,
                    'path': str(file_path),
                    'title': f"Daily Memory {date}",
                })
        else:
            # Recent memories (last 7 days)
            for i in range(7):
                d = datetime.now() - timedelta(days=i)
                date_str = d.strftime('%Y-%m-%d')
                file_path = memory_path / f"{date_str}.md"
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        results.append({
                            'type': 'daily_memory',
                            'date': date_str,
                            'path': str(file_path),
                            'title': f"Daily Memory {date_str}",
                            'preview': content[:200],
                        })
                    except:
                        pass
        
        return results
    
    def recall_entity_related(self, entity_name: str) -> List[Dict]:
        """
        Recall all documents related to a specific entity.
        
        Uses Graph Channel to find related entities, then BM25+Vector to find docs.
        """
        results = []
        
        # Use graph to find related entities
        graph_results = self.search.search_graph(entity_name, top_k=10)
        
        # Also search wiki for the entity
        wiki_results = self.search.search(entity_name, top_k=10)
        
        # Combine
        seen_paths = set()
        for doc_idx, score in wiki_results + graph_results:
            metadata = self.search.bm25_metadata[doc_idx]
            path = metadata['path']
            
            if path not in seen_paths:
                seen_paths.add(path)
                results.append({
                    'entity': entity_name,
                    'title': metadata['title'],
                    'path': path,
                    'score': score,
                })
        
        return results
    
    def get_recall_stats(self) -> Dict:
        """Get recall statistics for monitoring"""
        if not self.recent_recalls:
            return {
                'total_recalls': 0,
                'avg_latency_ms': 0,
                'top_sources': [],
                'top_entities': [],
            }
        
        total_recalls = len(self.recent_recalls)
        avg_latency = sum(r['latency_ms'] for r in self.recent_recalls) / total_recalls
        
        # Count sources
        source_counts = defaultdict(int)
        for r in self.recent_recalls:
            for s in r['sources']:
                source_counts[s] += 1
        
        top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Top entities
        top_entities = sorted(
            self.access_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'total_recalls': total_recalls,
            'avg_latency_ms': int(avg_latency),
            'top_sources': top_sources,
            'top_entities': top_entities,
        }
    
    def suggest_recall(self, context: Dict) -> Optional[str]:
        """
        Suggest a recall query based on current context.
        
        This is for proactive recall - suggesting searches based on conversation.
        
        Args:
            context: Current conversation context
        
        Returns:
            Suggested query string or None
        """
        # Check recent conversation for topics
        recent_topics = context.get('recent_topics', [])
        
        if recent_topics:
            # Suggest recall for least recently recalled topic
            for topic in reversed(recent_topics):
                if topic not in self.access_patterns:
                    return topic
                if self.access_patterns[topic] < 2:
                    return topic
        
        # Check date-based suggestions
        today = datetime.now().strftime('%Y-%m-%d')
        recent_memories = self.recall_daily_memory(date=today)
        
        if not recent_memories:
            return "今日 summary"
        
        return None


def inject_into_context(results: List[Dict], token_budget: int = 2000) -> str:
    """
    Convert search results into context string for injection.
    
    Args:
        results: List of search results from recall()
        token_budget: Maximum tokens to use
    
    Returns:
        Context string
    """
    context_parts = []
    total_tokens = 0
    
    for r in results:
        title = r['title']
        path = r['path']
        sources = '+'.join(r['sources'])
        
        # Estimate tokens
        tokens = len(title) + len(path) + 50
        if total_tokens + tokens > token_budget:
            break
        
        part = f"[{sources}] {title}\n  → {path}"
        context_parts.append(part)
        total_tokens += tokens
    
    if context_parts:
        header = "📚 Relevant Knowledge:\n"
        return header + "\n".join(context_parts)
    
    return ""


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Memory Recall Hook')
    parser.add_argument('--query', '-q', help='Query to recall')
    parser.add_argument('--stats', action='store_true', help='Show recall statistics')
    parser.add_argument('--wiki-path', default='/root/.openclaw/workspace/wiki')
    parser.add_argument('--memory-dir', default='/root/.openclaw/workspace/memory')
    parser.add_argument('--context', help='JSON context for smart triggering')
    
    args = parser.parse_args()
    
    hook = SmartRecallHook(
        wiki_path=args.wiki_path,
        memory_dir=args.memory_dir,
    )
    
    if args.stats:
        stats = hook.get_recall_stats()
        print("📊 Recall Statistics:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return
    
    if args.query:
        # Check if should trigger
        context = json.loads(args.context) if args.context else None
        should = hook.should_trigger(args.query, context)
        
        print(f"🔍 Query: {args.query}")
        print(f"   Trigger: {'✅ Yes' if should else '❌ No'}")
        
        if should:
            results = hook.recall(args.query, context)
            print(f"\n📚 Results ({len(results)}):")
            for i, r in enumerate(results, 1):
                sources = '+'.join(r['sources'])
                print(f"   {i}. [{sources}] {r['title']}")
                print(f"      {r['path']}")
            
            # Inject context
            ctx = inject_into_context(results)
            if ctx:
                print(f"\n📝 Context for injection:")
                print(ctx)
    else:
        print("Usage:")
        print("  python3 smart_recall_hook.py --query '古洞站'")
        print("  python3 smart_recall_hook.py --stats")
        print("  python3 smart_recall_hook.py --query '知識圖譜' --context '{\"topic\": \"OCM\"}'")


if __name__ == '__main__':
    main()