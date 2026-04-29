#!/usr/bin/env python3
"""
Unified News Collector
News Intelligence System - Phase 5

結合所有 sources：
1. Tavily Search API (AI news queries)
2. RSS Feeds (TechCrunch, MIT, HackerNews, etc.)

Output: combined items for scoring
"""

import os
import json
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.parent
CACHE_DIR = SCRIPT_DIR / "cache"

def search_tavily(query: str, max_results: int = 8) -> list:
    """用 Tavily API 搜索"""
    try:
        from tavily import TavilyClient
        api_key = os.environ.get('TAVILY_API_KEY', '')
        if not api_key:
            print(f"  ⚠️ Tavily API key not set")
            return []
        
        tavily = TavilyClient(api_key=api_key)
        results = tavily.search(
            query=query,
            max_results=max_results,
            days=7,  # Last 7 days
            include_answer=False,
            include_raw_content=False
        )
        
        items = []
        for r in results.get('results', []):
            items.append({
                'title': r.get('title', 'Untitled'),
                'link': r.get('url', ''),
                'published': r.get('published', datetime.now().strftime('%Y-%m-%d')),
                'summary': r.get('content', '')[:300],
                'source': r.get('source', 'Tavily'),
                'category': 'AI',
                'language': 'en',
                'source_type': 'search'  # Mark as search result
            })
        
        print(f"  ✅ Tavily: {len(items)} items for '{query[:40]}...'")
        return items
        
    except Exception as e:
        print(f"  ❌ Tavily error: {e}")
        return []

def load_rss_items() -> list:
    """載入 RSS feeds 結果"""
    rss_file = CACHE_DIR / "rss_combined.json"
    
    if not rss_file.exists():
        print(f"  ⚠️ No RSS cache found at {rss_file}")
        return []
    
    with open(rss_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    items = data.get('items', [])
    
    # Mark as RSS source
    for item in items:
        item['source_type'] = 'rss'
    
    print(f"  ✅ RSS: {len(items)} items loaded")
    return items

def deduplicate_items(items: list) -> list:
    """基於 title 相似度去重"""
    unique = []
    seen_titles = set()
    
    for item in items:
        title = item.get('title', '').lower()
        # 簡單去重：移除標點後對比
        title_clean = ''.join(c for c in title if c.isalnum() or c == ' ')
        
        if title_clean not in seen_titles and len(title_clean) > 10:
            seen_titles.add(title_clean)
            unique.append(item)
    
    removed = len(items) - len(unique)
    if removed > 0:
        print(f"  🔄 Deduplicated: {removed} duplicates removed")
    
    return unique

def main():
    """主函數"""
    print(f"📡 Unified News Collector - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_items = []
    
    # 1. Tavily Search (3 queries)
    print("\n📡 Source 1: Tavily Search API")
    queries = [
        "OpenAI GPT ChatGPT artificial intelligence news 2026",
        "Claude Anthropic Gemini Google AI news",
        "AI agent machine learning latest breakthroughs",
    ]
    
    for query in queries:
        items = search_tavily(query, max_results=8)
        all_items.extend(items)
    
    # 2. RSS Feeds
    print("\n📡 Source 2: RSS Feeds")
    rss_items = load_rss_items()
    all_items.extend(rss_items)
    
    # 3. Deduplicate
    print("\n🔄 Deduplicating...")
    unique_items = deduplicate_items(all_items)
    
    # 4. Save combined results
    combined_file = CACHE_DIR / "unified_combined.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump({
            'fetched_at': datetime.now().isoformat(),
            'total_items': len(unique_items),
            'sources': {
                'tavily': len([i for i in unique_items if i.get('source_type') == 'search']),
                'rss': len([i for i in unique_items if i.get('source_type') == 'rss'])
            },
            'items': unique_items
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 Summary:")
    print(f"  Total unique items: {len(unique_items)}")
    print(f"  Saved to: {combined_file}")
    
    return len(unique_items)

if __name__ == "__main__":
    main()
