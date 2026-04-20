#!/usr/bin/env python3
"""
Schema Migration System for OCM-Sup
Manages versioning and migration of wiki entity frontmatter schemas

Usage:
    python3 schema_migration.py --check      # Check current schema versions
    python3 schema_migration.py --migrate    # Run migrations
    python3 schema_migration.py --status      # Show migration status
"""
import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

WIKI_PATH = Path('/root/.openclaw/workspace/wiki')

# Schema version history
SCHEMA_VERSIONS = {
    'v1.0': {
        'date': '2026-04-13',
        'description': 'Initial schema with confidence and retention',
        'fields': ['confidence', 'retention'],
    },
    'v1.1': {
        'date': '2026-04-15',
        'description': 'Added aliases, relationships, entityType',
        'fields': ['confidence', 'retention', 'aliases', 'relationships', 'entityType'],
    },
    'v1.2': {
        'date': '2026-04-16',
        'description': 'Added lastAccessed and updatedAt',
        'fields': ['confidence', 'retention', 'aliases', 'relationships', 'entityType', 'lastAccessed', 'updatedAt'],
    },
    'v1.3': {
        'date': '2026-04-18',
        'description': 'Added supersedes/supersededBy for knowledge tracking',
        'fields': ['confidence', 'retention', 'aliases', 'relationships', 'entityType', 'lastAccessed', 'updatedAt', 'supersedes', 'supersededBy'],
    },
}

CURRENT_SCHEMA_VERSION = 'v1.3'


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


def get_schema_version(frontmatter: Dict) -> str:
    """Get schema version from frontmatter"""
    return frontmatter.get('schemaVersion', 'v1.0')


def set_schema_version(frontmatter: Dict, version: str) -> Dict:
    """Set schema version in frontmatter"""
    frontmatter['schemaVersion'] = version
    return frontmatter


def frontmatter_to_yaml(frontmatter: Dict) -> str:
    """Convert frontmatter dict to YAML string"""
    lines = ['---']
    for key, value in frontmatter.items():
        if isinstance(value, list):
            lines.append(f'{key}:')
            for item in value:
                lines.append(f'  - {item}')
        elif isinstance(value, dict):
            lines.append(f'{key}:')
            for k, v in value.items():
                lines.append(f'  {k}: {v}')
        else:
            lines.append(f'{key}: {value}')
    lines.append('---')
    return '\n'.join(lines)


def check_schema_status(wiki_path: Path) -> Dict[str, List[Path]]:
    """Check schema version status of all wiki entities"""
    status = {
        'v1.0': [], 'v1.1': [], 'v1.2': [], 'v1.3': [], 'unknown': []
    }
    
    for md_file in wiki_path.rglob('*.md'):
        # Skip non-entity files
        rel = md_file.relative_to(wiki_path)
        if 'entities' not in str(rel) and 'concepts' not in str(rel) and 'syntheses' not in str(rel):
            continue
        
        try:
            content = md_file.read_text(encoding='utf-8')
            frontmatter, _ = parse_frontmatter(content)
            version = get_schema_version(frontmatter)
            
            if version in status:
                status[version].append(md_file)
            else:
                status['unknown'].append(md_file)
        except Exception as e:
            status['unknown'].append(md_file)
    
    return status


def migrate_v1_0_to_v1_1(frontmatter: Dict) -> Dict:
    """Migrate from v1.0 to v1.1 - add aliases, relationships, entityType"""
    # Aliases - derive from title if not present
    if 'aliases' not in frontmatter:
        title = frontmatter.get('title', '')
        if title:
            frontmatter['aliases'] = [title]
    
    # Relationships - initialize empty
    if 'relationships' not in frontmatter:
        frontmatter['relationships'] = []
    
    # EntityType - derive from path or title
    if 'entityType' not in frontmatter:
        title = frontmatter.get('title', '').lower()
        if '期哥' in title or 'jacky' in title.lower():
            frontmatter['entityType'] = 'person'
        elif 'station' in title or '站' in title:
            frontmatter['entityType'] = 'location'
        elif 'project' in title or '項目' in title:
            frontmatter['entityType'] = 'project'
        else:
            frontmatter['entityType'] = 'concept'
    
    return frontmatter


def migrate_v1_1_to_v1_2(frontmatter: Dict) -> Dict:
    """Migrate from v1.1 to v1.2 - add lastAccessed and updatedAt"""
    if 'lastAccessed' not in frontmatter:
        # Use updated if available, else current date
        frontmatter['lastAccessed'] = frontmatter.get('updatedAt', datetime.now().strftime('%Y-%m-%d'))
    
    if 'updatedAt' not in frontmatter:
        frontmatter['updatedAt'] = frontmatter.get('lastAccessed', datetime.now().strftime('%Y-%m-%d'))
    
    return frontmatter


def migrate_v1_2_to_v1_3(frontmatter: Dict) -> Dict:
    """Migrate from v1.2 to v1.3 - add supersedes/supersededBy"""
    if 'supersedes' not in frontmatter:
        frontmatter['supersedes'] = []
    
    if 'supersededBy' not in frontmatter:
        frontmatter['supersededBy'] = []
    
    return frontmatter


def migrate_entity(file_path: Path, dry_run: bool = True) -> Tuple[bool, str]:
    """Migrate a single entity file to current schema"""
    try:
        content = file_path.read_text(encoding='utf-8')
        frontmatter, body = parse_frontmatter(content)
        
        old_version = get_schema_version(frontmatter)
        
        if old_version == CURRENT_SCHEMA_VERSION:
            return False, "Already at current version"
        
        # Run migrations in order
        migrations = [
            ('v1.0', migrate_v1_0_to_v1_1),
            ('v1.1', migrate_v1_1_to_v1_2),
            ('v1.2', migrate_v1_2_to_v1_3),
        ]
        
        for target_version, migration_fn in migrations:
            if old_version < target_version:
                frontmatter = migration_fn(frontmatter)
                old_version = target_version
        
        # Set final schema version
        frontmatter = set_schema_version(frontmatter, CURRENT_SCHEMA_VERSION)
        
        if not dry_run:
            new_content = frontmatter_to_yaml(frontmatter) + '\n' + body
            file_path.write_text(new_content, encoding='utf-8')
        
        return True, f"Migrated from {get_schema_version({'schemaVersion': old_version})} to {CURRENT_SCHEMA_VERSION}"
    
    except Exception as e:
        return False, f"Error: {str(e)}"


def run_migration(dry_run: bool = True, specific_version: str = None) -> Dict:
    """Run schema migration"""
    status = check_schema_status(WIKI_PATH)
    
    results = {
        'migrated': [],
        'skipped': [],
        'errors': [],
        'summary': {},
    }
    
    # Migrate entities that are not at current version
    for version in ['v1.0', 'v1.1', 'v1.2', 'unknown']:
        for file_path in status.get(version, []):
            migrated, message = migrate_entity(file_path, dry_run)
            
            if migrated:
                results['migrated'].append({
                    'file': str(file_path.relative_to(WIKI_PATH)),
                    'message': message,
                })
            else:
                results['skipped'].append({
                    'file': str(file_path.relative_to(WIKI_PATH)),
                    'message': message,
                })
    
    # Summary
    results['summary'] = {
        'total_checked': sum(len(v) for v in status.values()),
        'at_current_version': len(status.get(CURRENT_SCHEMA_VERSION, [])),
        'needs_migration': len(results['migrated']),
        'skipped': len(results['skipped']),
        'errors': len(results['errors']),
    }
    
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='OCM-Sup Schema Migration')
    parser.add_argument('--check', action='store_true', help='Check schema versions')
    parser.add_argument('--migrate', action='store_true', help='Run migration (dry-run by default)')
    parser.add_argument('--apply', action='store_true', help='Apply migration for real')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    
    args = parser.parse_args()
    
    if args.check or args.status:
        status = check_schema_status(WIKI_PATH)
        print(f"\n📊 Schema Version Status (Current: {CURRENT_SCHEMA_VERSION})")
        print(f"   Total entities: {sum(len(v) for v in status.values())}")
        print()
        for version in ['v1.0', 'v1.1', 'v1.2', 'v1.3', 'unknown']:
            files = status.get(version, [])
            if files:
                print(f"   {version}: {len(files)} files")
                if len(files) <= 5:
                    for f in files:
                        print(f"      - {f.relative_to(WIKI_PATH)}")
                else:
                    for f in files[:3]:
                        print(f"      - {f.relative_to(WIKI_PATH)}")
                    print(f"      ... and {len(files) - 3} more")
        
        print()
        print("Schema Version History:")
        for ver, info in SCHEMA_VERSIONS.items():
            print(f"   {ver} ({info['date']}): {info['description']}")
        print()
    
    if args.migrate:
        print("\n🔍 Running migration check (dry-run)...")
        results = run_migration(dry_run=True)
        print(f"\n   Would migrate: {results['summary']['needs_migration']} files")
        print(f"   Already current: {results['summary']['at_current_version']} files")
        
        if results['migrated']:
            print("\n   Files to migrate:")
            for item in results['migrated'][:10]:
                print(f"      - {item['file']}: {item['message']}")
        
        print("\n   Use --apply to actually migrate")
    
    if args.apply:
        print("\n🚀 Applying migrations...")
        results = run_migration(dry_run=False)
        print(f"\n✅ Migrated: {results['summary']['needs_migration']} files")
        
        if results['migrated']:
            print("\n   Migrated files:")
            for item in results['migrated'][:20]:
                print(f"      - {item['file']}")
        
        if results['errors']:
            print(f"\n❌ Errors: {len(results['errors'])}")
            for item in results['errors']:
                print(f"      - {item['file']}: {item['message']}")


if __name__ == '__main__':
    main()