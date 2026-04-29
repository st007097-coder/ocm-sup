#!/usr/bin/env python3
"""
Phase 2: Deduplicator
News Intelligence System

Rolling 7-day Events DB 去重機制
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# Paths
SCRIPT_DIR = Path(__file__).parent.parent
CACHE_DIR = SCRIPT_DIR / "cache"
ROLLING_DB = CACHE_DIR / "rolling_events.json"

def load_rolling_db() -> dict:
    """載入 Rolling Events DB"""
    if ROLLING_DB.exists():
        with open(ROLLING_DB, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'events': {},
        'updated_at': datetime.now().isoformat()
    }

def save_rolling_db(db: dict):
    """保存 Rolling Events DB"""
    db['updated_at'] = datetime.now().isoformat()
    with open(ROLLING_DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def clean_old_events(db: dict, days: int = 7):
    """清理超過 7 天嘅 events"""
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    
    events = db.get('events', {})
    cleaned_count = 0
    
    for date_str in list(events.keys()):
        if date_str < cutoff_str:
            del events[date_str]
            cleaned_count += 1
    
    if cleaned_count > 0:
        print(f"🗑️  Cleaned {cleaned_count} old event days (>{days} days)")
    
    return db

def extract_keywords(text: str) -> set:
    """提取關鍵詞用於相似度比較"""
    import re
    text = text.lower()
    words = re.findall(r'\b[a-z]{4,}\b', text)
    stopwords = {'this', 'that', 'with', 'from', 'they', 'been', 'have', 'were', 'will', 'your', 'what', 'about', 'more', 'than', 'just', 'when', 'they', 'there', 'from'}
    return set(words) - stopwords

def is_similar(new_text: str, existing_events: List[str], threshold: float = 0.5) -> bool:
    """
    檢查新文本是否與現有事件相似
    只比較過去 2 天嘅事件，避免同一天內重複
    """
    new_keywords = extract_keywords(new_text)
    
    for event in existing_events:
        existing_keywords = extract_keywords(event)
        
        if not new_keywords or not existing_keywords:
            continue
        
        intersection = len(new_keywords & existing_keywords)
        union = len(new_keywords | existing_keywords)
        
        if union > 0:
            similarity = intersection / union
            if similarity >= threshold:
                return True
    
    return False

def deduplicate(items: List[dict]) -> tuple:
    """
    去重主函數
    
    只比較過去 2 天嘅事件，避免同一天內去重太多
    返回: (unique_items, duplicates_count, old_items_count)
    """
    db = load_rolling_db()
    db = clean_old_events(db, days=7)
    
    # 取得過去 2 天嘅事件（不包括今天）
    today = datetime.now()
    yesterday = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    day_before = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    
    recent_events = []
    for date_str, events in db.get('events', {}).items():
        if date_str in [yesterday, day_before]:
            recent_events.extend(events)
    
    unique_items = []
    duplicates_count = 0
    old_items_count = 0
    
    for item in items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        
        # 檢查是否相似於過去 2 天嘅事件
        if is_similar(text, recent_events):
            item['is_old'] = True
            item['dedup_reason'] = 'similar_to_recent_event'
            old_items_count += 1
        else:
            item['is_old'] = False
            item['dedup_reason'] = None
            unique_items.append(item)
    
    # 清理滾動 DB（只保留 7 天）
    db = clean_old_events(db, days=7)
    save_rolling_db(db)
    
    return unique_items, duplicates_count, old_items_count

def add_to_db(items: List[dict]):
    """
    將新 items 加入滾動 DB
    通常喺 dedup之後調用
    """
    db = load_rolling_db()
    
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in db['events']:
        db['events'][today] = []
    
    for item in items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        db['events'][today].append(text[:200])
    
    save_rolling_db(db)
    print(f"📝 Added {len(items)} items to rolling DB (today: {today})")

def main():
    """測試主函數"""
    from rss_fetcher import CACHE_DIR
    
    print(f"🔄 Deduplicator Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    rss_file = CACHE_DIR / "rss_combined.json"
    
    if not rss_file.exists():
        print("❌ No RSS cache found. Run rss_fetcher.py first.")
        return
    
    with open(rss_file, 'r', encoding='utf-8') as f:
        rss_data = json.load(f)
    
    items = rss_data.get('items', [])
    print(f"📥 Input: {len(items)} items")
    
    unique_items, duplicates_count, old_items_count = deduplicate(items)
    
    print(f"\n📊 Deduplication Results:")
    print(f"  ✅ Unique (new): {len(unique_items)}")
    print(f"  🔁 Duplicates: {duplicates_count}")
    print(f"  📰 Old (similar to recent events): {old_items_count}")
    print(f"  📉 Total removed: {duplicates_count + old_items_count}")
    
    # Add unique items to DB
    if unique_items:
        add_to_db(unique_items)
    
    print(f"\n📋 Sample unique items:")
    for item in unique_items[:5]:
        print(f"  - [{item['source']}] {item['title'][:70]}...")

if __name__ == "__main__":
    main()
