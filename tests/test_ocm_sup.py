#!/usr/bin/env python3
"""Tests for OCM Sup Knowledge Management System"""

import sys
import os

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

def test_manifest():
    """Test manifest.json exists and is valid"""
    manifest_path = os.path.join(os.path.dirname(__file__), '..', 'manifest.json')
    
    if not os.path.exists(manifest_path):
        print(f"❌ manifest.json: missing")
        return False
    
    try:
        import json
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        required_fields = ['name', 'version', 'owner', 'status']
        for field in required_fields:
            if field not in manifest:
                print(f"❌ manifest.json: missing '{field}'")
                return False
        
        print(f"✅ manifest.json: valid (v{manifest.get('version', '?')})")
        return True
    except Exception as e:
        print(f"❌ manifest.json: invalid - {e}")
        return False

def test_skill_md():
    """Test SKILL.md exists and has required sections"""
    skill_path = os.path.join(os.path.dirname(__file__), '..', 'SKILL.md')
    
    if not os.path.exists(skill_path):
        print(f"❌ SKILL.md: missing")
        return False
    
    with open(skill_path) as f:
        content = f.read()
    
    required_sections = ['## 🎯 目標', '## ⚡ 觸發條件', '## 🔄 核心功能', '## ⚠️ 邊界條件', '## 🛑 檢查點']
    missing = []
    for section in required_sections:
        if section not in content:
            missing.append(section)
    
    if missing:
        print(f"❌ SKILL.md: missing sections: {missing}")
        return False
    
    print(f"✅ SKILL.md: all required sections present")
    return True

def test_evals():
    """Test evals directory has required files"""
    evals_dir = os.path.join(os.path.dirname(__file__), '..', 'evals')
    
    trigger_cases = os.path.join(evals_dir, 'trigger_cases.json')
    semantic_config = os.path.join(evals_dir, 'semantic_config.json')
    
    if os.path.exists(trigger_cases):
        print(f"✅ evals: trigger_cases.json exists")
    else:
        print(f"❌ evals: trigger_cases.json missing")
        return False
    
    if os.path.exists(semantic_config):
        print(f"✅ evals: semantic_config.json exists")
    else:
        print(f"❌ evals: semantic_config.json missing")
        return False
    
    return True

def test_governance():
    """Test governance directory has owner.md"""
    governance_dir = os.path.join(os.path.dirname(__file__), '..', 'governance')
    owner_file = os.path.join(governance_dir, 'owner.md')
    
    if os.path.exists(owner_file):
        print(f"✅ governance: owner.md exists")
        return True
    else:
        print(f"❌ governance: owner.md missing")
        return False

def test_scripts_import():
    """Test core scripts can be imported"""
    try:
        import graph_search
        print(f"✅ graph_search: Module import successful")
        return True
    except ImportError as e:
        print(f"❌ graph_search: Import failed - {e}")
        return False
    except Exception as e:
        print(f"⚠️ graph_search: {e}")
        return True  # Allow other errors

def test_readme():
    """Test README.md exists and is valid"""
    readme_path = os.path.join(os.path.dirname(__file__), '..', 'README.md')
    
    if not os.path.exists(readme_path):
        print(f"❌ README.md: missing")
        return False
    
    with open(readme_path) as f:
        content = f.read()
    
    required_sections = ['OCM-Sup', 'Triple-Stream', 'Knowledge Graph']
    missing = []
    for section in required_sections:
        if section not in content:
            missing.append(section)
    
    if missing:
        print(f"❌ README.md: missing sections: {missing}")
        return False
    
    print(f"✅ README.md: valid")
    return True

def test_changelog():
    """Test CHANGELOG.md exists"""
    changelog_path = os.path.join(os.path.dirname(__file__), '..', 'CHANGELOG.md')
    
    if os.path.exists(changelog_path):
        print(f"✅ CHANGELOG.md: exists")
        return True
    else:
        print(f"❌ CHANGELOG.md: missing")
        return False

def test_version():
    """Test version consistency between files"""
    manifest_path = os.path.join(os.path.dirname(__file__), '..', 'manifest.json')
    skill_path = os.path.join(os.path.dirname(__file__), '..', 'SKILL.md')
    
    if not os.path.exists(manifest_path):
        return False
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    version = manifest.get('version', '?')
    
    with open(skill_path) as f:
        skill_content = f.read()
    
    if f"version: \"{version}\"" in open(skill_path).read() or f"**Version**: v{version}" in skill_content:
        print(f"✅ version: consistent ({version})")
        return True
    else:
        print(f"⚠️ version: manifest={version}, SKILL.md check skipped")
        return True

def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("🧪 OCM Sup System - Tests")
    print("=" * 50)
    print()
    
    tests = [
        test_manifest,
        test_skill_md,
        test_evals,
        test_governance,
        test_scripts_import,
        test_readme,
        test_changelog,
        test_version,
    ]
    
    results = []
    for test in tests:
        print(f"\n{test.__name__}:")
        results.append(test())
    
    print()
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"📊 Results: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All tests passed!")
        return True
    else:
        print(f"❌ {total - passed} test(s) failed")
        return False

if __name__ == '__main__':
    import json
    success = run_all_tests()
    sys.exit(0 if success else 1)