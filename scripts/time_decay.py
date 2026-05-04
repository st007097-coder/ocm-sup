#!/usr/bin/env python3
"""
Time-based Decay System for OCM-Sup
Replaces per-access decay with age-based decay

Concept:
- All memories have a base half-life (e.g., 30 days)
- Decay rate increases as memory ages (aging acceleration)
- Access still helps but doesn't fully reset decay
- Hot memories (recently accessed + young) stay fresh
- Cold memories (not accessed + old) decay faster

Usage:
    python3 time_decay.py --check          # Check decay status of all entities
    python3 time_decay.py --simulate       # Simulate decay without applying
    python3 time_decay.py --apply          # Apply decay (mark cold entities)
    python3 time_decay.py --gc             # Garbage collect very old decayed entities
"""
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math

WIKI_PATH = Path('/home/jacky/.openclaw/workspace/wiki')

# Decay parameters
BASE_HALF_LIFE_DAYS = 30  # Base half-life for all memories
AGING_ACCELERATION = 1.5   # How much faster old memories decay (per 30 days)
ACCESS_BOOST_DAYS = 7      # Each access adds ~7 days of effective life
MIN_DECAY_THRESHOLD = 0.1  # Below this score, entity is "decayed"
VERY_COLD_THRESHOLD = 0.05 # Below this, eligible for garbage collection


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """Parse YAML frontmatter from markdown content"""
    match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not match:
        return {}, content
    
    frontmatter = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            frontmatter[key.strip()] = value.strip().strip('"\'')
    
    body = match.group(2)
    return frontmatter, body


def get_date_from_frontmatter(frontmatter: Dict) -> Optional[datetime]:
    """Extract date from frontmatter (lastAccessed or created date)"""
    # Try lastAccessed first
    date_str = frontmatter.get('lastAccessed', '')
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            pass
    
    # Try created
    date_str = frontmatter.get('created', '')
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            pass
    
    # Try updatedAt
    date_str = frontmatter.get('updatedAt', '')
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            pass
    
    return None


def calculate_decay_score(last_accessed: datetime, now: datetime = None) -> float:
    """
    Calculate decay score using time-based decay model.
    
    Score formula:
    - base_score = 1.0 (fresh)
    - Each day reduces score by decay_rate
    - decay_rate increases with age (aging acceleration)
    
    Score = 1.0 / (1 + (age_days / half_life) ^ aging_acceleration)
    
    Returns score between 0 and 1.
    """
    if now is None:
        now = datetime.now()
    
    age = (now - last_accessed).days
    
    if age <= 0:
        return 1.0
    
    # Normalized age (age in half-lives)
    normalized_age = age / BASE_HALF_LIFE_DAYS
    
    # Time-based decay with aging acceleration
    decay_score = 1.0 / (1.0 + normalized_age ** AGING_ACCELERATION)
    
    return decay_score


def calculate_access_boost(last_accessed: datetime, access_count: int = 1) -> float:
    """
    Calculate access boost.
    Each access extends effective life by ~ACCESS_BOOST_DAYS.
    """
    boost = access_count * ACCESS_BOOST_DAYS
    # Convert to equivalent age reduction
    return boost


def compute_effective_score(last_accessed: datetime, now: datetime = None, access_count: int = 1) -> float:
    """
    Compute effective decay score with access boost.
    
    1. Calculate base time-decay score
    2. Add access boost (extend effective life)
    3. Return final score
    """
    if now is None:
        now = datetime.now()
    
    age = (now - last_accessed).days
    
    # Access boost reduces effective age
    effective_age = max(0, age - calculate_access_boost(last_accessed, access_count))
    
    if effective_age <= 0:
        return 1.0
    
    normalized_age = effective_age / BASE_HALF_LIFE_DAYS
    score = 1.0 / (1.0 + normalized_age ** AGING_ACCELERATION)
    
    return score


def check_entity_decay(file_path: Path) -> Dict:
    """Check decay status of a single entity"""
    try:
        content = file_path.read_text(encoding='utf-8')
        frontmatter, body = parse_frontmatter(content)
        
        last_accessed = get_date_from_frontmatter(frontmatter)
        
        if last_accessed is None:
            return {
                'path': str(file_path.relative_to(WIKI_PATH)),
                'status': 'unknown_date',
                'score': 0.0,
                'last_accessed': None,
                'age_days': None,
            }
        
        now = datetime.now()
        age_days = (now - last_accessed).days
        
        time_decay_score = calculate_decay_score(last_accessed, now)
        
        # Check for retention field (per-access decay)
        retention = frontmatter.get('retention', None)
        if retention:
            try:
                retention_val = float(retention)
                # Per-access score is lower bound
                time_decay_score = min(time_decay_score, retention_val)
            except:
                pass
        
        # Determine status
        if time_decay_score >= 0.7:
            status = 'hot'
        elif time_decay_score >= 0.3:
            status = 'warm'
        elif time_decay_score >= MIN_DECAY_THRESHOLD:
            status = 'cold'
        else:
            status = 'very_cold'
        
        return {
            'path': str(file_path.relative_to(WIKI_PATH)),
            'status': status,
            'score': round(time_decay_score, 3),
            'last_accessed': last_accessed.strftime('%Y-%m-%d'),
            'age_days': age_days,
            'title': frontmatter.get('title', ''),
        }
    
    except Exception as e:
        return {
            'path': str(file_path.relative_to(WIKI_PATH)),
            'status': 'error',
            'score': 0.0,
            'error': str(e),
        }


def check_all_entities(wiki_path: Path) -> Dict[str, List[Dict]]:
    """Check decay status of all wiki entities"""
    status = {
        'hot': [],
        'warm': [],
        'cold': [],
        'very_cold': [],
        'unknown_date': [],
        'error': [],
    }
    
    for md_file in wiki_path.rglob('*.md'):
        # Only check entities
        rel = md_file.relative_to(wiki_path)
        if 'entities' not in str(rel) and 'concepts' not in str(rel):
            continue
        
        result = check_entity_decay(md_file)
        status[result['status']].append(result)
    
    return status


def format_decay_report(status: Dict[str, List[Dict]]) -> str:
    """Format decay status as a readable report"""
    total = sum(len(v) for v in status.values())
    
    lines = [
        f"\n📊 Time-Based Decay Report",
        f"   Parameters: half_life={BASE_HALF_LIFE_DAYS}days, aging_accel={AGING_ACCELERATION}, access_boost={ACCESS_BOOST_DAYS}days",
        f"   Total entities checked: {total}",
        f"",
    ]
    
    for label, label_desc in [('hot', '🔥 Hot (score 0.7+)'), ('warm', '🌡️ Warm (0.3-0.7)'), ('cold', '❄️ Cold (0.1-0.3)'), ('very_cold', '💀 Very Cold (<0.1)')]:
        if status[label]:
            items = status[label]
            lines.append(f"   {label_desc}: {len(items)}")
            for item in items[:5]:
                lines.append(f"      [{item['score']}] {item.get('title', item['path'])} ({item['age_days']}d old)")
            if len(items) > 5:
                lines.append(f"      ... and {len(items) - 5} more")
            lines.append("")
    
    if status['unknown_date']:
        lines.append(f"   ⚠️ Unknown date: {len(status['unknown_date'])}")
        for item in status['unknown_date'][:3]:
            lines.append(f"      - {item['path']}")
        lines.append("")
    
    return '\n'.join(lines)


def apply_decay_markers(wiki_path: Path, dry_run: bool = True) -> Dict:
    """
    Apply decay scores to entity frontmatter.
    Updates 'decayScore' and 'decayStatus' fields.
    """
    status = check_all_entities(wiki_path)
    
    updated = []
    skipped = []
    
    for label, items in status.items():
        if label in ['unknown_date', 'error']:
            skipped.extend(items)
            continue
        
        for item in items:
            file_path = wiki_path / item['path']
            
            if dry_run:
                updated.append({
                    'path': item['path'],
                    'action': 'would_update',
                    'status': item['status'],
                    'score': item['score'],
                })
            else:
                try:
                    content = file_path.read_text(encoding='utf-8')
                    frontmatter, body = parse_frontmatter(content)
                    
                    frontmatter['decayScore'] = str(item['score'])
                    frontmatter['decayStatus'] = item['status']
                    frontmatter['decayChecked'] = datetime.now().strftime('%Y-%m-%d')
                    
                    # Write back
                    new_content = '---\n'
                    for k, v in frontmatter.items():
                        new_content += f'{k}: {v}\n'
                    new_content += '---\n' + body
                    
                    file_path.write_text(new_content, encoding='utf-8')
                    
                    updated.append({
                        'path': item['path'],
                        'action': 'updated',
                        'status': item['status'],
                        'score': item['score'],
                    })
                except Exception as e:
                    skipped.append({
                        'path': item['path'],
                        'error': str(e),
                    })
    
    return {
        'updated': updated,
        'skipped': skipped,
        'summary': {
            'total': sum(len(v) for v in status.values()),
            'hot': len(status['hot']),
            'warm': len(status['warm']),
            'cold': len(status['cold']),
            'very_cold': len(status['very_cold']),
        }
    }


def garbage_collect(wiki_path: Path, dry_run: bool = True) -> List[Dict]:
    """
    Garbage collect very cold entities (below VERY_COLD_THRESHOLD).
    Options:
    - archive: move to a .archive folder
    - delete: permanently delete
    - downgrade: reduce quality score
    """
    status = check_all_entities(wiki_path)
    very_cold = status.get('very_cold', [])
    
    results = []
    
    for item in very_cold:
        file_path = wiki_path / item['path']
        
        if dry_run:
            results.append({
                'path': item['path'],
                'action': 'would_archive',
                'score': item['score'],
                'age_days': item['age_days'],
            })
        else:
            try:
                archive_dir = wiki_path / '.archive'
                archive_dir.mkdir(exist_ok=True)
                
                archive_path = archive_dir / file_path.name
                file_path.rename(archive_path)
                
                results.append({
                    'path': item['path'],
                    'action': 'archived_to',
                    'archive_path': str(archive_path.relative_to(wiki_path)),
                    'score': item['score'],
                    'age_days': item['age_days'],
                })
            except Exception as e:
                results.append({
                    'path': item['path'],
                    'action': 'error',
                    'error': str(e),
                })
    
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='OCM-Sup Time-Based Decay System')
    parser.add_argument('--check', action='store_true', help='Check decay status of all entities')
    parser.add_argument('--simulate', action='store_true', help='Simulate decay without applying')
    parser.add_argument('--apply', action='store_true', help='Apply decay markers to entities')
    parser.add_argument('--gc', action='store_true', help='Garbage collect very cold entities')
    parser.add_argument('--gc-apply', action='store_true', help='Actually perform garbage collection')
    
    args = parser.parse_args()
    
    if args.check:
        status = check_all_entities(WIKI_PATH)
        print(format_decay_report(status))
    
    if args.simulate:
        print("\n🔍 Simulating decay (dry-run)...")
        results = apply_decay_markers(WIKI_PATH, dry_run=True)
        print(f"\n   Would update: {len(results['updated'])} entities")
        print(f"   Skipped: {len(results['skipped'])}")
        
        print(f"\n   Summary: hot={results['summary']['hot']}, warm={results['summary']['warm']}, cold={results['summary']['cold']}, very_cold={results['summary']['very_cold']}")
        
        if results['updated']:
            print("\n   Sample updates:")
            for item in results['updated'][:10]:
                print(f"      [{item['status']}] {item['path']}: score={item['score']}")
        
        print("\n   Use --apply to actually apply markers")
    
    if args.apply:
        print("\n🚀 Applying decay markers...")
        results = apply_decay_markers(WIKI_PATH, dry_run=False)
        print(f"\n✅ Updated: {len(results['updated'])} entities")
        
        if results['updated']:
            print("\n   Updated files:")
            for item in results['updated'][:20]:
                print(f"      [{item['status']}] {item['path']}: score={item['score']}")
        
        if results['skipped']:
            print(f"\n   Skipped: {len(results['skipped'])}")
    
    if args.gc:
        print("\n🗑️ Simulating garbage collection (dry-run)...")
        results = garbage_collect(WIKI_PATH, dry_run=True)
        print(f"\n   Would archive: {len(results)} very cold entities")
        
        for item in results[:10]:
            print(f"      [{item['score']}] {item['path']} ({item['age_days']}d old)")
        
        print("\n   Use --gc-apply to actually archive")
    
    if args.gc_apply:
        print("\n🗑️ Performing garbage collection...")
        results = garbage_collect(WIKI_PATH, dry_run=False)
        print(f"\n✅ Archived: {len(results)} very cold entities")
        
        for item in results:
            print(f"      → {item.get('archive_path', item['path'])}")


if __name__ == '__main__':
    main()