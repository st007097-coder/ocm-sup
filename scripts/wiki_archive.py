#!/usr/bin/env python3
"""
Wiki Archive Script
OCM Sup - Weekly Archive Backup

Usage:
    python3 scripts/wiki_archive.py              # Create archive with today's date
    python3 scripts/wiki_archive.py --list       # List all archives
    python3 scripts/wiki_archive.py --restore DATE  # Restore from archive
    python3 scripts/wiki_archive.py --latest     # Restore from latest archive
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# Archive directory
ARCHIVE_BASE = Path("~/.openclaw/ocm-sup/wiki_archives").expanduser()
WIKI_DIR = Path("~/.openclaw/workspace/wiki")

def get_archive_path(date_str=None):
    """Get archive path for a date."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    return ARCHIVE_BASE / f"wiki_archive_{date_str}"

def create_archive(date_str=None):
    """Create archive of wiki directory."""
    archive_path = get_archive_path(date_str)
    
    if archive_path.exists():
        print(f"⚠️  Archive already exists: {archive_path}")
        response = input("Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return False
    
    print(f"📦 Creating archive: {archive_path}")
    
    # Create parent directory
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy wiki directory
    if WIKI_DIR.exists():
        shutil.copytree(WIKI_DIR, archive_path, dirs_exist_ok=True)
        
        # Count files
        file_count = sum(1 for _ in archive_path.rglob("*") if _.is_file())
        print(f"✅ Archive created: {file_count} files")
    else:
        print(f"⚠️  Wiki directory not found: {WIKI_DIR}")
        return False
    
    # Save metadata
    metadata = {
        "date": date_str or datetime.now().strftime("%Y-%m-%d"),
        "created_at": datetime.now().isoformat(),
        "wiki_path": str(WIKI_DIR),
        "file_count": file_count
    }
    metadata_path = archive_path / "archive_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"📝 Metadata saved: {metadata_path}")
    return True

def list_archives():
    """List all archives."""
    if not ARCHIVE_BASE.exists():
        print("❌ No archives found.")
        return
    
    archives = sorted(ARCHIVE_BASE.glob("wiki_archive_*"))
    
    if not archives:
        print("❌ No archives found.")
        return
    
    print(f"\n📚 Found {len(archives)} archives:\n")
    print(f"{'Date':<15} {'Files':<10} {'Size':<15}")
    print("-" * 40)
    
    for archive in archives:
        date_str = archive.name.replace("wiki_archive_", "")
        
        # Count files
        file_count = sum(1 for _ in archive.rglob("*") if _.is_file())
        
        # Get size
        total_size = sum(f.stat().st_size for f in archive.rglob("*") if f.is_file())
        size_str = format_size(total_size)
        
        print(f"{date_str:<15} {file_count:<10} {size_str:<15}")

def format_size(size):
    """Format file size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def restore_archive(date_str):
    """Restore from an archive."""
    archive_path = get_archive_path(date_str)
    
    if not archive_path.exists():
        print(f"❌ Archive not found: {archive_path}")
        return False
    
    print(f"♻️  Restoring from: {archive_path}")
    
    # Backup current wiki first
    backup_path = WIKI_DIR.parent / f"wiki_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"💾 Backup current wiki to: {backup_path}")
    if WIKI_DIR.exists():
        shutil.copytree(WIKI_DIR, backup_path, dirs_exist_ok=True)
    
    # Restore
    print(f"📂 Restoring wiki from archive...")
    if WIKI_DIR.exists():
        shutil.rmtree(WIKI_DIR)
    shutil.copytree(archive_path, WIKI_DIR)
    
    print(f"✅ Restore complete!")
    return True

def restore_latest():
    """Restore from the latest archive."""
    if not ARCHIVE_BASE.exists():
        print("❌ No archives found.")
        return
    
    archives = sorted(ARCHIVE_BASE.glob("wiki_archive_*"))
    
    if not archives:
        print("❌ No archives found.")
        return
    
    latest = archives[-1]
    date_str = latest.name.replace("wiki_archive_", "")
    
    print(f"♻️  Restoring from latest archive: {date_str}")
    restore_archive(date_str)

def main():
    parser = argparse.ArgumentParser(description="OCM Sup Wiki Archive Tool")
    parser.add_argument("--list", action="store_true", help="List all archives")
    parser.add_argument("--restore", metavar="DATE", help="Restore from archive (YYYY-MM-DD)")
    parser.add_argument("--latest", action="store_true", help="Restore from latest archive")
    
    args = parser.parse_args()
    
    if args.list:
        list_archives()
    elif args.restore:
        restore_archive(args.restore)
    elif args.latest:
        restore_latest()
    else:
        # Create archive by default
        create_archive()

if __name__ == "__main__":
    main()
