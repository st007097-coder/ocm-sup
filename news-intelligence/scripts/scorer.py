#!/usr/bin/env python3
"""
Phase 3: Interest Scorer
News Intelligence System

基於關鍵詞嘅興趣評分系統
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Paths
SCRIPT_DIR = Path(__file__).parent.parent
CACHE_DIR = SCRIPT_DIR / "cache"

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
    
    print(f"🎯 Interest Scorer Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Load RSS data
    rss_file = CACHE_DIR / "rss_combined.json"
    
    if not rss_file.exists():
        print("❌ No RSS cache found. Run rss_fetcher.py first.")
        return
    
    with open(rss_file, 'r', encoding='utf-8') as f:
        rss_data = json.load(f)
    
    items = rss_data.get('items', [])
    print(f"📥 Input: {len(items)} items")
    
    # Deduplicate first
    unique_items, dups, old = deduplicate(items)
    print(f"📊 After dedup: {len(unique_items)} unique items")
    
    # Score
    scored_items = score_items(unique_items)
    
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
