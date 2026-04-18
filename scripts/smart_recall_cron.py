#!/usr/bin/env python3
"""
Smart Recall Cron Job
Pre-loads context for hot topics based on access patterns

Usage:
    # Run once
    python3 smart_recall_cron.py
    
    # Run with custom hot topics
    python3 smart_recall_cron.py --topics "古洞站,期哥,阿星"
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/root/.openclaw/workspace/skills/triple-stream-search/scripts')

from smart_recall_hook import SmartRecallHook, inject_into_context

def get_hot_topics(hook, min_access_count=2):
    """Get hot topics from access patterns"""
    hot = [(k, v) for k, v in hook.access_patterns.items() if v >= min_access_count]
    hot.sort(key=lambda x: x[1], reverse=True)
    return [k for k, v in hot[:10]]

def precache_context_for_topics(topics):
    """Pre-cache context for given topics"""
    hook = SmartRecallHook()
    
    results = {}
    for topic in topics:
        try:
            if hook.should_trigger(topic):
                recall_results = hook.recall(topic)
                context = inject_into_context(recall_results)
                results[topic] = {
                    'recall_count': len(recall_results),
                    'context': context,
                    'timestamp': datetime.now().isoformat(),
                }
                print(f"✅ Pre-cached: {topic} ({len(recall_results)} results)")
            else:
                print(f"⚠️  Skipped: {topic} (not triggering)")
        except Exception as e:
            print(f"❌ Error caching {topic}: {e}")
            results[topic] = {'error': str(e)}
    
    return results

def save_cache(results):
    """Save pre-cached context to disk"""
    cache_path = Path("/root/.openclaw/scripts/.recall_cache.json")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Cache saved to {cache_path}")
    return cache_path

def load_cache():
    """Load pre-cached context from disk"""
    cache_path = Path("/root/.openclaw/scripts/.recall_cache.json")
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def main():
    parser = argparse.ArgumentParser(description='Smart Recall Cron Job')
    parser.add_argument('--topics', help='Comma-separated topics (default: hot topics from access patterns)')
    parser.add_argument('--min-access', type=int, default=2, help='Minimum access count for hot topics')
    parser.add_argument('--save', action='store_true', help='Save cache to disk')
    parser.add_argument('--load', action='store_true', help='Load and display cached context')
    
    args = parser.parse_args()
    
    print("🚀 Smart Recall Cron Job")
    print(f"   Time: {datetime.now().isoformat()}")
    print()
    
    if args.load:
        print("📂 Loading cached context...")
        cache = load_cache()
        print(f"   Found {len(cache)} cached topics:")
        for topic, data in cache.items():
            if 'error' not in data:
                print(f"   - {topic}: {data.get('recall_count', 0)} results")
            else:
                print(f"   - {topic}: ERROR")
        return
    
    # Get topics to pre-cache
    if args.topics:
        topics = [t.strip() for t in args.topics.split(',')]
    else:
        # Use hot topics from access patterns
        hook = SmartRecallHook()
        topics = get_hot_topics(hook, args.min_access)
        
        if not topics:
            print("📊 No hot topics found (access count < {})".format(args.min_access))
            print("   Topics will need to be accessed first before they become 'hot'")
            print()
            # Default to known important topics
            topics = ['期哥', '古洞站', '阿星', 'OCM Sup', 'Triple-Stream Search']
            print(f"   Using default topics: {topics}")
        else:
            print(f"📊 Hot topics found: {topics}")
    
    print()
    
    # Pre-cache context for each topic
    results = precache_context_for_topics(topics)
    
    # Save if requested
    if args.save or not args.topics:
        save_cache(results)
    
    # Print summary
    print()
    print("📈 Summary:")
    success = sum(1 for r in results.values() if 'error' not in r)
    print(f"   Success: {success}/{len(results)}")
    
    # Print cached context for first topic as example
    if results and not args.topics:
        first_topic = list(results.keys())[0]
        if 'context' in results[first_topic]:
            print(f"\n📝 Example context for '{first_topic}':")
            print(results[first_topic]['context'][:500] + "...")

if __name__ == '__main__':
    main()