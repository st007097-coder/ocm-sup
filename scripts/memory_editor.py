#!/usr/bin/env python3
"""
Memory Editor CLI
OCM Sup - Interactive Memory View/Edit/Search

Usage:
    python3 scripts/memory_editor.py              # Interactive mode
    python3 scripts/memory_editor.py --search "query"   # Search
    python3 scripts/memory_editor.py --list             # List all
    python3 scripts/memory_editor.py --view FILE       # View file
    python3 scripts/memory_editor.py --edit FILE       # Edit file
    python3 scripts/memory_editor.py --delete FILE     # Delete file
"""

import os
import sys
import json
import readline
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

WIKI_DIR = Path("~/.openclaw/workspace/wiki").expanduser()
MEMORY_FILE = Path("~/.openclaw/workspace/MEMORY.md").expanduser()

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def color(text, code):
    return f"{code}{text}{RESET}"

def search_memory(query: str) -> List[Path]:
    """Search memory files."""
    results = []
    query_lower = query.lower()
    
    for md_file in WIKI_DIR.rglob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                if query_lower in content:
                    # Calculate relevance (simple word count)
                    count = content.count(query_lower)
                    results.append((md_file, count))
        except:
            pass
    
    # Sort by relevance
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]

def list_memories(category: Optional[str] = None) -> List[Path]:
    """List all memory files."""
    memories = []
    
    if category:
        category_path = WIKI_DIR / category
        if category_path.exists():
            memories = list(category_path.rglob("*.md"))
    else:
        memories = list(WIKI_DIR.rglob("*.md"))
    
    # Filter out archives, imports, etc
    memories = [m for m in memories if "archive" not in str(m) and "imports" not in str(m)]
    
    return sorted(memories, key=lambda x: x.stat().st_mtime, reverse=True)

def view_file(file_path: Path) -> str:
    """View file contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def edit_file_interactive(file_path: Path):
    """Edit file interactively."""
    content = view_file(file_path)
    
    print(f"\n{color('Editing: ' + str(file_path), BLUE + BOLD)}")
    print(color('=' * 60, BLUE))
    print(content[:500] + "..." if len(content) > 500 else content)
    print(color('=' * 60, BLUE))
    
    print(f"\n{color('Enter new content (or press Enter to keep current):', YELLOW)}")
    print(f"{color('Type :wq to save and quit, :q to quit without saving', RED)}")
    
    lines = content.split('\n')
    
    # Simple line editing
    for i, line in enumerate(lines[:10]):
        print(f"{i+1:3d}: {line}")
    
    if len(lines) > 10:
        print(f"... ({len(lines) - 10} more lines)")
    
    print()
    new_lines = []
    print("Enter lines (empty line to finish, :wq to save, :q to cancel):")
    
    while True:
        try:
            line = input(f"{len(new_lines)+1:3d}: ")
            if line == ":wq":
                break
            elif line == ":q":
                return None
            elif line == "":
                # Empty line - finish input
                break
            else:
                new_lines.append(line)
        except EOFError:
            break
    
    if new_lines:
        final_content = '\n'.join(new_lines)
    else:
        final_content = content
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    return final_content

def delete_file_interactive(file_path: Path) -> bool:
    """Delete file with confirmation."""
    print(f"\n{color('⚠️  Delete file?', RED + BOLD)}")
    print(f"  {file_path}")
    print()
    response = input("Type 'yes' to confirm: ")
    
    if response.lower() == 'yes':
        try:
            file_path.unlink()
            print(f"{color('✅ Deleted: ' + str(file_path), GREEN)}")
            return True
        except Exception as e:
            print(f"{color('❌ Error: ' + str(e), RED)}")
            return False
    else:
        print("Cancelled.")
        return False

def interactive_mode():
    """Interactive memory editor."""
    print(f"\n{color('🧠 OCM Sup Memory Editor', BLUE + BOLD)}")
    print(f"{color('Wiki: ' + str(WIKI_DIR), BLUE)}")
    print()
    
    categories = [d.name for d in WIKI_DIR.iterdir() if d.is_dir()] if WIKI_DIR.exists() else []
    
    while True:
        print(f"\n{color('Commands:', BOLD)}")
        print("  1. Search    - Search memories")
        print("  2. List      - List all memories")
        print("  3. View      - View a file")
        print("  4. Edit      - Edit a file")
        print("  5. Delete    - Delete a file")
        print("  6. Categories - Show categories")
        print("  7. Stats     - Show memory stats")
        print("  8. Quit      - Exit")
        print()
        
        try:
            choice = input(f"{color('> ', GREEN)}").strip()
        except EOFError:
            break
        
        if choice == '1' or choice.lower().startswith('search'):
            query = input("Search query: ").strip()
            if query:
                results = search_memory(query)
                print(f"\n{color(f'Found {len(results)} results:', BOLD)}")
                for i, r in enumerate(results[:10], 1):
                    print(f"  {i}. {r.relative_to(WIKI_DIR)}")
                if len(results) > 10:
                    print(f"  ... and {len(results) - 10} more")
        
        elif choice == '2' or choice.lower().startswith('list'):
            results = list_memories()
            print(f"\n{color(f'Found {len(results)} memory files:', BOLD)}")
            for i, r in enumerate(results[:20], 1):
                print(f"  {i}. {r.relative_to(WIKI_DIR)}")
            if len(results) > 20:
                print(f"  ... and {len(results) - 20} more")
        
        elif choice == '3' or choice.lower().startswith('view'):
            path_str = input("File path (relative to wiki): ").strip()
            if path_str:
                file_path = WIKI_DIR / path_str
                if file_path.exists():
                    content = view_file(file_path)
                    print(f"\n{color('=' * 60, BLUE)}")
                    print(content[:1000] + "..." if len(content) > 1000 else content)
                    print(f"{color('=' * 60, BLUE)}")
                else:
                    print(f"{color('❌ File not found', RED)}")
        
        elif choice == '4' or choice.lower().startswith('edit'):
            path_str = input("File path (relative to wiki): ").strip()
            if path_str:
                file_path = WIKI_DIR / path_str
                if file_path.exists():
                    edit_file_interactive(file_path)
                else:
                    print(f"{color('❌ File not found', RED)}")
        
        elif choice == '5' or choice.lower().startswith('delete'):
            path_str = input("File path (relative to wiki): ").strip()
            if path_str:
                file_path = WIKI_DIR / path_str
                if file_path.exists():
                    delete_file_interactive(file_path)
                else:
                    print(f"{color('❌ File not found', RED)}")
        
        elif choice == '6' or choice.lower().startswith('cat'):
            print(f"\n{color('Categories:', BOLD)}")
            for cat in categories:
                cat_path = WIKI_DIR / cat
                count = len(list(cat_path.rglob("*.md")))
                print(f"  {cat}: {count} files")
        
        elif choice == '7' or choice.lower().startswith('stat'):
            results = list_memories()
            total_size = sum(f.stat().st_size for f in results)
            print(f"\n{color('Memory Stats:', BOLD)}")
            print(f"  Total files: {len(results)}")
            print(f"  Total size: {total_size / 1024:.1f} KB")
            print(f"  Wiki: {WIKI_DIR}")
        
        elif choice == '8' or choice.lower().startswith('quit'):
            print("Goodbye!")
            break

def main():
    parser = argparse.ArgumentParser(description="OCM Sup Memory Editor")
    parser.add_argument("--search", "-s", help="Search memories")
    parser.add_argument("--list", "-l", action="store_true", help="List all memories")
    parser.add_argument("--view", "-v", help="View a file")
    parser.add_argument("--edit", "-e", help="Edit a file")
    parser.add_argument("--delete", "-d", help="Delete a file")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    
    args = parser.parse_args()
    
    if args.search:
        results = search_memory(args.search)
        print(f"Found {len(results)} results:")
        for r in results[:20]:
            print(f"  {r}")
    
    elif args.list:
        results = list_memories()
        print(f"Found {len(results)} memory files:")
        for r in results[:50]:
            print(f"  {r}")
    
    elif args.view:
        file_path = Path(args.view)
        if not file_path.is_absolute():
            file_path = WIKI_DIR / args.view
        if file_path.exists():
            print(view_file(file_path))
        else:
            print(f"File not found: {file_path}")
    
    elif args.edit:
        file_path = Path(args.edit)
        if not file_path.is_absolute():
            file_path = WIKI_DIR / args.edit
        if file_path.exists():
            edit_file_interactive(file_path)
        else:
            print(f"File not found: {file_path}")
    
    elif args.delete:
        file_path = Path(args.delete)
        if not file_path.is_absolute():
            file_path = WIKI_DIR / args.delete
        if file_path.exists():
            delete_file_interactive(file_path)
        else:
            print(f"File not found: {file_path}")
    
    elif args.stats:
        results = list_memories()
        total_size = sum(f.stat().st_size for f in results)
        print(f"Memory Stats:")
        print(f"  Total files: {len(results)}")
        print(f"  Total size: {total_size / 1024:.1f} KB")
    
    else:
        interactive_mode()

if __name__ == "__main__":
    main()
