#!/usr/bin/env python3
"""
Memory Import Script
OCM Sup - Import from other LLMs

Usage:
    python3 scripts/memory_import.py --file exported_memory.json
    python3 scripts/memory_import.py --dir chatgpt_exports/
    python3 scripts/memory_import.py --format chatgpt --file memory.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import re

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

WIKI_DIR = Path("~/.openclaw/workspace/wiki").expanduser()
IMPORT_DIR = WIKI_DIR / "imports"

def import_chatgpt_format(file_path):
    """Import from ChatGPT export format."""
    print(f"📥 Importing ChatGPT format: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    imported = 0
    
    # ChatGPT format: {"conversations": [{"text": "...", "date": "..."}]}
    if "conversations" in data:
        for conv in data["conversations"]:
            text = conv.get("text", "")
            if not text:
                continue
            
            # Create filename from first 50 chars
            title = text[:50].replace("/", "_").replace("\\", "_")
            filename = f"chatgpt_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{imported}.md"
            
            content = f"""---
title: "ChatGPT Import"
source: "ChatGPT Export"
imported: {datetime.now().isoformat()}
---

{text}
"""
            
            output_path = IMPORT_DIR / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            imported += 1
    
    # Alternative format: array of objects
    elif isinstance(data, list):
        for item in data:
            text = item.get("text") or item.get("content") or item.get("message", "")
            if not text:
                continue
            
            title = text[:50].replace("/", "_").replace("\\", "_")
            filename = f"chatgpt_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{imported}.md"
            
            content = f"""---
title: "ChatGPT Import"
source: "ChatGPT Export"
imported: {datetime.now().isoformat()}
---

{text}
"""
            
            output_path = IMPORT_DIR / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            imported += 1
    
    print(f"✅ Imported {imported} items")
    return imported

def import_markdown_dir(dir_path):
    """Import all markdown files from a directory."""
    print(f"📥 Importing markdown files from: {dir_path}")
    
    dir_path = Path(dir_path)
    md_files = list(dir_path.glob("*.md")) + list(dir_path.glob("*.txt"))
    
    imported = 0
    
    for file_path in md_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create new filename with import prefix
        filename = f"imported_{datetime.now().strftime('%Y%m%d')}_{file_path.name}"
        
        # Add import metadata if not already present
        if content.startswith("---"):
            # Already has frontmatter, add import info
            parts = content.split("---", 2)
            frontmatter = parts[1] + '\nimported: {}\nimported_from: "{}"'.format(
                datetime.now().isoformat(), str(file_path))
            content = "---\n" + frontmatter + "---\n" + parts[2] if len(parts) > 2 else content
        else:
            content = f"""---
title: "{file_path.stem}"
source: "Import"
imported: {datetime.now().isoformat()}
imported_from: "{file_path}"
---

{content}
"""
        
        output_path = IMPORT_DIR / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        imported += 1
    
    print(f"✅ Imported {imported} files from directory")
    return imported

def import_generic_json(file_path):
    """Import from generic JSON format."""
    print(f"📥 Importing generic JSON: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    imported = 0
    
    # Try common formats
    items = []
    
    if isinstance(data, dict):
        if "memories" in data:
            items = data["memories"]
        elif "facts" in data:
            items = data["facts"]
        elif "notes" in data:
            items = data["notes"]
        elif "entries" in data:
            items = data["entries"]
        else:
            # Single item
            items = [data]
    elif isinstance(data, list):
        items = data
    
    for item in items:
        # Try to extract text
        text = item.get("text") or item.get("content") or item.get("note") or item.get("fact", "")
        if not text:
            continue
        
        title = item.get("title", text[:50])
        title = title.replace("/", "_").replace("\\", "_")
        
        filename = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{imported}.md"
        
        content = f"""---
title: "{title}"
source: "JSON Import"
imported: {datetime.now().isoformat()}
---

{text}
"""
        
        output_path = IMPORT_DIR / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        imported += 1
    
    print(f"✅ Imported {imported} items")
    return imported

def main():
    parser = argparse.ArgumentParser(description="OCM Sup Memory Import Tool")
    parser.add_argument("--file", "-f", help="Import from file")
    parser.add_argument("--dir", "-d", help="Import from directory")
    parser.add_argument("--format", choices=["chatgpt", "markdown", "json", "auto"], 
                       default="auto", help="Input format")
    
    args = parser.parse_args()
    
    if not args.file and not args.dir:
        parser.print_help()
        print("\n📝 Example usage:")
        print("  python3 memory_import.py --file chatgpt_export.json --format chatgpt")
        print("  python3 memory_import.py --dir /path/to/markdown/files/")
        return
    
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return
        
        if args.format == "chatgpt" or (args.format == "auto" and file_path.suffix == ".json"):
            import_chatgpt_format(file_path)
        else:
            import_generic_json(file_path)
    
    if args.dir:
        dir_path = Path(args.dir)
        if not dir_path.exists():
            print(f"❌ Directory not found: {dir_path}")
            return
        
        import_markdown_dir(dir_path)
    
    print(f"\n📂 Imported files saved to: {IMPORT_DIR}")

if __name__ == "__main__":
    main()
