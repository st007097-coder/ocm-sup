#!/usr/bin/env python3
"""
Fix malformed YAML in entity files where `target` and `type` 
are at top level instead of nested under relationship dict.

Before (malformed):
  relationships: 
  - direction: outgoing
  target: 古洞站

After (correct):
  relationships: 
  - direction: outgoing
    target: 古洞站
"""

import os
import re
from pathlib import Path


def fix_entity_yaml(filepath: Path) -> tuple[bool, list]:
    """Fix YAML indentation issue in entity file.
    
    Returns: (changed: bool, list of fixes applied)
    """
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return False, []
    
    original = content
    fixes = []
    
    # Split into lines
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Look for "relationships:" followed by a list item with "direction:"
        if 'relationships:' in line and i + 1 < len(lines):
            # Add the relationships: line
            fixed_lines.append(line)
            i += 1
            
            # Now process what follows
            while i < len(lines):
                current = lines[i]
                current_stripped = current.strip()
                next_stripped = lines[i + 1].strip() if i + 1 < len(lines) else ''
                
                # If this line is "- direction: xxx" (list item with direction)
                if current_stripped.startswith('- direction:'):
                    fixed_lines.append(current)
                    i += 1
                    
                    # Look at subsequent lines - they should be indented properly
                    while i < len(lines):
                        next_line = lines[i]
                        next_line_stripped = next_line.strip()
                        
                        # Stop if we hit another list item
                        if next_line_stripped.startswith('- '):
                            break
                        
                        # Stop if we hit an empty line followed by non-target/type
                        if next_line_stripped == '':
                            # Check if next non-empty line is target/type at wrong level
                            j = i + 1
                            while j < len(lines) and lines[j].strip() == '':
                                j += 1
                            if j >= len(lines):
                                break
                            next_content = lines[j].strip()
                            if not next_content.startswith('target:') and not next_content.startswith('type:'):
                                break
                        
                        # If line is target: or type: at 0-space indent (wrong level)
                        # it should be indented to 4 spaces (under the list item)
                        if next_line_stripped.startswith('target:') or next_line_stripped.startswith('type:'):
                            # Check current indentation
                            indent = len(next_line) - len(next_line.lstrip())
                            
                            # If at 0 spaces, it needs to be 4 spaces
                            if indent == 0:
                                fixed_lines.append('    ' + next_line_stripped)
                                fixes.append(f"  Fixed indent: {next_line_stripped[:50]}")
                                i += 1
                                continue
                            elif indent < 4 and not next_line.startswith(' '):
                                # String starts with target: but no proper indent
                                fixed_lines.append('    ' + next_line_stripped)
                                fixes.append(f"  Fixed indent: {next_line_stripped[:50]}")
                                i += 1
                                continue
                        
                        # Line is fine as-is
                        fixed_lines.append(next_line)
                        i += 1
                        
                        # If this was an empty line, stop processing this block
                        if next_line_stripped == '':
                            break
                else:
                    # Not a direction list item
                    fixed_lines.append(current)
                    i += 1
                    break
        else:
            fixed_lines.append(line)
            i += 1
    
    fixed_content = '\n'.join(fixed_lines)
    
    if fixed_content != original:
        filepath.write_text(fixed_content, encoding='utf-8')
        return True, fixes
    
    return False, fixes


def main():
    wiki_path = Path("/home/jacky/.openclaw/workspace/wiki")
    
    # Find all markdown files that might be entities
    md_files = []
    
    for root, dirs, files in os.walk(wiki_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.endswith('.md'):
                md_files.append(Path(root) / file)
    
    print(f"Found {len(md_files)} markdown files to check")
    
    checked = 0
    fixed = 0
    
    for filepath in md_files:
        checked += 1
        changed, fixes = fix_entity_yaml(filepath)
        if changed:
            rel_path = filepath.relative_to(wiki_path)
            print(f"✅ Fixed: {rel_path}")
            for f in fixes:
                print(f"   {f}")
            fixed += 1
    
    print(f"\n📊 Summary:")
    print(f"   Checked: {checked}")
    print(f"   Fixed: {fixed}")


if __name__ == "__main__":
    main()