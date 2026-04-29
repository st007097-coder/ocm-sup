#!/usr/bin/env python3
"""
Phase 1: RSS Fetcher
News Intelligence System

收集 RSS feeds 的新聞並緩存
"""

import os
import sys
import json
import yaml
from datetime import datetime
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("feedparser not installed, installing...")
    os.system("pip install feedparser")
    import feedparser

# Paths
SCRIPT_DIR = Path(__file__).parent.parent
CACHE_DIR = SCRIPT_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
RSS_CACHE = CACHE_DIR / "rss_cache"
RSS_CACHE.mkdir(exist_ok=True)

def load_feeds():
    """載入 RSS feeds 配置"""
    config_path = SCRIPT_DIR / "sources" / "rss_feeds.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('feeds', [])

def fetch_feed(feed_config: dict) -> list:
    """fetch 單個 feed"""
    try:
        print(f"📥 Fetching: {feed_config['name']}...")
        
        feed = feedparser.parse(feed_config['url'])
        
        items = []
        for entry in feed.entries[:20]:  # 每個 feed 最多 20 條
            # 提取 publish date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    from time import mktime
                    published = datetime.fromtimestamp(
                        mktime(entry.published_parsed)
                    ).strftime('%Y-%m-%d %H:%M')
                except:
                    published = datetime.now().strftime('%Y-%m-%d')
            else:
                published = datetime.now().strftime('%Y-%m-%d')
            
            # 提取 link
            link = entry.get('link', '')
            
            # 提取 summary/description
            summary = ''
            if hasattr(entry, 'summary'):
                summary = entry.summary
            elif hasattr(entry, 'description'):
                summary = entry.description
            elif hasattr(entry, 'content'):
                summary = entry.content[0].value if entry.content else ''
            
            # 清理 HTML
            import re
            summary = re.sub(r'<[^>]+>', '', summary)  # Remove HTML tags
            summary = summary.strip()[:500]  # Truncate to 500 chars
            
            item = {
                'title': entry.get('title', 'Untitled'),
                'link': link,
                'published': published,
                'summary': summary,
                'source': feed_config['name'],
                'category': feed_config.get('category', 'General'),
                'language': feed_config.get('language', 'en'),
            }
            items.append(item)
        
        print(f"  ✅ Got {len(items)} items from {feed_config['name']}")
        return items
        
    except Exception as e:
        print(f"  ❌ Error fetching {feed_config['name']}: {e}")
        return []

def save_cache(items: list, feed_name: str):
    """保存到本地 cache"""
    cache_file = RSS_CACHE / f"{feed_name.replace(' ', '_')}.json"
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump({
            'feed': feed_name,
            'fetched_at': datetime.now().isoformat(),
            'items': items
        }, f, ensure_ascii=False, indent=2)
    return cache_file

def main():
    """主函數"""
    print(f"📰 RSS Fetcher - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    feeds = load_feeds()
    print(f"📋 Found {len(feeds)} feeds configured\n")
    
    all_items = []
    results = []
    
    for feed_config in feeds:
        items = fetch_feed(feed_config)
        
        if items:
            # Save to cache
            cache_file = save_cache(items, feed_config['name'])
            results.append({
                'source': feed_config['name'],
                'count': len(items),
                'cache_file': str(cache_file)
            })
            all_items.extend(items)
    
    # Save combined results
    combined_file = CACHE_DIR / "rss_combined.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump({
            'fetched_at': datetime.now().isoformat(),
            'total_items': len(all_items),
            'sources': len(results),
            'items': all_items
        }, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 50)
    print(f"📊 Summary:")
    print(f"  Total items collected: {len(all_items)}")
    for r in results:
        print(f"  - {r['source']}: {r['count']} items")
    print(f"\n  Saved to: {combined_file}")
    
    return len(all_items)

if __name__ == "__main__":
    main()
