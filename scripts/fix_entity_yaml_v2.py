#!/usr/bin/env python3
"""
Fix malformed YAML in entity files where `target` and `type` 
are at top level instead of nested under relationship dict.

Correct YAML structure for relationships:
  relationships: 
  - direction: outgoing
    target: xxx
    type: yyy

Common error: target/type at 0-space indent (document level) instead of 2-space (under list item)
"""

import os
import re
import yaml
from pathlib import Path


def fix_entity_yaml_v2(filepath: Path) -> tuple[bool, list]:
    """Fix YAML indentation issue in entity file.
    
    Returns: (changed: bool, list of fixes applied)
    """
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return False, [f"Read error: {e}"]
    
    original = content
    fixes = []
    
    # Split into lines
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Look for relationships: followed by list items
        if stripped == 'relationships:':
            fixed_lines.append(line)
            i += 1
            
            # Process the relationships block
            while i < len(lines):
                current = lines[i]
                current_stripped = current.strip()
                
                # Stop if we hit a non-list-item, non-target/type line
                # (we're done with the relationships block)
                if current_stripped and not current_stripped.startswith('- ') and \
                   not current_stripped.startswith('target:') and \
                   not current_stripped.startswith('type:'):
                    # This is content outside relationships block
                    # But first, check if we need to fix any remaining target/type at wrong indent
                    break
                
                # If this is a list item with direction
                if current_stripped.startswith('- direction:'):
                    fixed_lines.append(current)
                    i += 1
                    
                    # Now process following lines that belong to this list item
                    while i < len(lines):
                        next_line = lines[i]
                        next_stripped = next_line.strip()
                        
                        # Stop if we hit another list item
                        if next_stripped.startswith('- '):
                            break
                        
                        # Stop if we hit an empty line or a field that's not target/type
                        if not next_stripped:
                            fixed_lines.append(next_line)
                            i += 1
                            break
                        
                        if not next_stripped.startswith('target:') and \
                           not next_stripped.startswith('type:'):
                            # This is some other field - stop processing as part of list item
                            break
                        
                        # At this point, next_line is target: or type:
                        # Check if it's at wrong indentation (0 spaces)
                        indent = len(next_line) - len(next_line.lstrip())
                        
                        if indent == 0:
                            # This is wrong! Should be indented to be under list item
                            # List item is at 2 spaces (for "- direction"), content should be at 4
                            fixed_lines.append('    ' + next_stripped)
                            fixes.append(f"Fixed indent: {next_stripped}")
                            i += 1
                        elif indent < 2:
                            # Also wrong - needs proper indent
                            fixed_lines.append('    ' + next_stripped)
                            fixes.append(f"Fixed indent: {next_stripped}")
                            i += 1
                        else:
                            # Seems OK
                            fixed_lines.append(next_line)
                            i += 1
                elif current_stripped.startswith('target:') or current_stripped.startswith('type:'):
                    # target/type at this level without a preceding - direction line
                    # This shouldn't normally happen in well-formed YAML, but if it does
                    # and it's at 0 indent, it might be the malformed case
                    indent = len(current) - len(current.lstrip())
                    if indent == 0:
                        # Skip this - it's likely part of the malformed structure
                        # but we handle it in the loop above
                        fixed_lines.append(current)
                        i += 1
                    else:
                        fixed_lines.append(current)
                        i += 1
                else:
                    # Something else - add and move on
                    fixed_lines.append(current)
                    i += 1
        else:
            fixed_lines.append(line)
            i += 1
    
    fixed_content = '\n'.join(fixed_lines)
    
    if fixed_content != original:
        # Validate YAML before writing
        try:
            # Only validate frontmatter
            parts = fixed_content.split('---')
            if len(parts) >= 3:
                fm = parts[1]
                yaml.safe_load(fm)
            elif len(parts) == 2:
                fm = parts[1]
                yaml.safe_load(fm)
        except yaml.YAMLError as e:
            return False, [f"YAML validation failed: {e}"]
        
        filepath.write_text(fixed_content, encoding='utf-8')
        return True, fixes
    
    return False, fixes


def check_and_fix_file(filepath: Path) -> tuple[bool, bool, str]:
    """Check if file has YAML issues and fix if needed.
    
    Returns: (was_broken, was_fixed, message)
    """
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return False, False, f"Read error: {e}"
    
    # Try to parse frontmatter
    parts = content.split('---')
    if len(parts) < 2:
        return False, False, "No frontmatter"
    
    try:
        fm = parts[1]
        yaml.safe_load(fm)
        # YAML is valid - check if relationships are correct
        data = yaml.safe_load(fm)
        rels = data.get('relationships', [])
        if isinstance(rels, list) and len(rels) > 0:
            for rel in rels:
                if isinstance(rel, dict):
                    # If relationship has direction but no target, might be broken
                    if 'direction' in rel and 'target' not in rel:
                        # This is suspicious - the target might be at top level
                        # Check if there's a top-level target
                        if 'target' in data:
                            return True, False, "Has broken target in rel"
        return False, False, "OK"
    except yaml.YAMLError as e:
        return True, False, f"YAML broken: {str(e)[:50]}"


def main():
    wiki_path = Path("/root/.openclaw/workspace/wiki")
    
    # Find all markdown files
    md_files = list(wiki_path.rglob("*.md"))
    
    print(f"Found {len(md_files)} markdown files")
    
    broken = 0
    fixed = 0
    checked = 0
    
    for filepath in md_files:
        checked += 1
        
        was_broken, was_fixed, msg = check_and_fix_file(filepath)
        
        if was_broken:
            broken += 1
            # Try to fix
            changed, fixes = fix_entity_yaml_v2(filepath)
            if changed:
                fixed += 1
                print(f"✅ Fixed: {filepath.relative_to(wiki_path)}")
                for f in fixes:
                    print(f"   {f}")
            else:
                print(f"❌ Could not fix: {filepath.relative_to(wiki_path)} - {msg}")
    
    print(f"\n📊 Summary:")
    print(f"   Checked: {checked}")
    print(f"   Broken: {broken}")
    print(f"   Fixed: {fixed}")


if __name__ == "__main__":
    main()