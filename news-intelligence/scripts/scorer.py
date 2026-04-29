#!/usr/bin/env python3
"""
Phase 3: Interest Scorer
News Intelligence System

基於關鍵詞嘅興趣評分系統
"""

import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# Paths
SCRIPT_DIR = Path(__file__).parent.parent
CACHE_DIR = SCRIPT_DIR / "cache"

# 7-day freshness filter
FRESHNESS_DAYS = 7

# Default scoring rules (can be configured)
SCORING_RULES = {
    # Category keywords: (score, keywords)
    "major_ai_model": {
        "score": 3,
        "keywords": ["gpt", "claude", "gemini", "deepseek", "llama", "mistral", "ai model", "language model", "frontier model", "openai", "anthropic", "google ai"]
    },
    "ai_agent": {
        "score": 2,
        "keywords": ["ai agent", "agentic", "agent", "autonomous", "multi-agent", "agentic ai", "crewai", "langchain", "autoGPT", "babyagi"]
    },
    "ai_framework": {
        "score": 2,
        "keywords": ["framework", "sdk", "library", "toolkit", "platform", "open source", "github"]
    },
    "product_tool": {
        "score": 2,
        "keywords": ["launch", "release", "new product", "announce", "beta", "available now", "introducing", "launches"]
    },
    "industry_trend": {
        "score": 1,
        "keywords": ["trend", "market", "investment", "funding", "raise", "deal", "acquisition", "merger", "ipo", "regulation", "policy", "government", "china", "us ", "eu "]
    },
    "research_paper": {
        "score": 1,
        "keywords": ["paper", "research", "study", "arxiv", "benchmark", "dataset", "study shows", "findings", "discovery"]
    }
}

def score_item(item: dict) -> dict:
    """
    為單個新聞評分
    
    返回包含 score, level, score_breakdown 的 item
    """
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    
    total_score = 0
    score_breakdown = {}
    
    for category, rule in SCORING_RULES.items():
        score = rule["score"]
        keywords = rule["keywords"]
        
        found_keywords = [kw for kw in keywords if kw.lower() in text]
        
        if found_keywords:
            # Multiply score by number of matched keywords (capped)
            category_score = min(score * len(found_keywords), score * 2)
            total_score += category_score
            score_breakdown[category] = {
                "score": category_score,
                "matched": found_keywords
            }
    
    # Determine level
    if total_score >= 8:
        level = "🔥 HEADLINE"
    elif total_score >= 5:
        level = "⭐ IMPORTANT"
    elif total_score >= 3:
        level = "📌 NOTABLE"
    else:
        level = "📝 GENERAL"
    
    item['score'] = total_score
    item['level'] = level
    item['score_breakdown'] = score_breakdown
    
    return item

def is_fresh(item: dict, days: int = FRESHNESS_DAYS) -> bool:
    """
    檢查新聞係咪喺指定天數內
    返回 True 如果係 fresh
    """
    pub_date_str = item.get('published', '')
    
    if not pub_date_str:
        # 如果冇日期，保守啲當佢係 fresh
        return True
    
    try:
        # 嘗試解析日期 (格式: YYYY-MM-DD HH:MM)
        pub_date_str = pub_date_str[:16]  # 取前面 YYYY-MM-DD HH:MM
        pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d %H:%M')
        cutoff = datetime.now() - timedelta(days=days)
        return pub_date >= cutoff
    except:
        # 解析失敗，當佢係 fresh
        return True

def filter_fresh(items: List[dict], days: int = FRESHNESS_DAYS) -> tuple:
    """
    過濾出指定天數內既新聞
    返回 (fresh_items, old_items_count)
    """
    fresh_items = []
    old_count = 0
    
    for item in items:
        if is_fresh(item, days):
            fresh_items.append(item)
        else:
            old_count += 1
    
    return fresh_items, old_count

def score_items(items: List[dict]) -> List[dict]:
    """為所有新聞評分"""
    scored_items = []
    
    for item in items:
        scored_item = score_item(item)
        scored_items.append(scored_item)
    
    # Sort by score descending
    scored_items.sort(key=lambda x: x['score'], reverse=True)
    
    return scored_items

def main():
    """測試主函數"""
    from deduplicator import deduplicate
    
    print(f"🎯 Interest Scorer - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Load unified data (from unified_collector.py)
    # Falls back to rss_combined.json if unified not available
    unified_file = CACHE_DIR / "unified_combined.json"
    rss_file = CACHE_DIR / "rss_combined.json"
    
    source_file = unified_file if unified_file.exists() else rss_file
    
    if not source_file.exists():
        print(f"❌ No cache found. Run unified_collector.py or rss_fetcher.py first.")
        return
    
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    items = data.get('items', [])
    print(f"📥 Input: {len(items)} items from {source_file.name}")
    
    # Check source breakdown if available
    if 'sources' in data:
        print(f"   Sources: {data['sources']}")
    
    # Deduplicate (safety dedup even though unified_collector already did)
    unique_items, dups, old = deduplicate(items)
    print(f"📊 After dedup: {len(unique_items)} unique items")
    
    # Filter to last 7 days only
    fresh_items, old_count = filter_fresh(unique_items, days=FRESHNESS_DAYS)
    print(f"📅 After freshness filter ({FRESHNESS_DAYS} days): {len(fresh_items)} fresh, {old_count} old removed")
    
    if not fresh_items:
        print("❌ No fresh news in the last 7 days!")
        return
    
    # Score
    scored_items = score_items(fresh_items)
    
    # Summary by level
    levels = {"🔥 HEADLINE": [], "⭐ IMPORTANT": [], "📌 NOTABLE": [], "📝 GENERAL": []}
    
    for item in scored_items:
        levels[item['level']].append(item)
    
    print(f"\n📊 Scoring Results:")
    print(f"  🔥 HEADLINE: {len(levels['🔥 HEADLINE'])}")
    print(f"  ⭐ IMPORTANT: {len(levels['⭐ IMPORTANT'])}")
    print(f"  📌 NOTABLE: {len(levels['📌 NOTABLE'])}")
    print(f"  📝 GENERAL: {len(levels['📝 GENERAL'])}")
    
    # Show top items
    print(f"\n🔥 Top 5 Headlines:")
    for item in scored_items[:5]:
        print(f"  [{item['score']}pts] {item['title'][:70]}...")
    
    # Save scored items
    output_file = CACHE_DIR / "scored_items.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'scored_at': datetime.now().isoformat(),
            'total_items': len(scored_items),
            'items': scored_items
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 Saved to: {output_file}")

if __name__ == "__main__":
    main()
