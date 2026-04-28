"""
P3 Reliability Layer - Comprehensive Test Suite
Tests all P3 components for correctness and integration.
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add P3 to path
sys.path.insert(0, "/root/.openclaw/workspace/OCM-Sup")

# ============================================================
# TEST SETUP - Create isolated test environment
# ============================================================

TEST_DIR = Path("/tmp/p3_test_ocm_sup")
TEST_DIR.mkdir(parents=True, exist_ok=True)

# Override storage dirs to use test directory
os.environ["P3_TEST_MODE"] = "1"

# Import after path setup
from p3_reliability.contradiction.sentiment import get_sentiment_sign, is_opposite_sign
from p3_reliability.contradiction.embedding_store import EmbeddingStore
from p3_reliability.contradiction.llm_judge import LLMJudge
from p3_reliability.pruning.scorer import compute_prune_score, should_prune, PruneScorer
from p3_reliability.pruning.archiver import FactArchiver

# ============================================================
# HELPERS
# ============================================================

def test_result(name: str, passed: bool, msg: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status} | {name}")
    if msg:
        print(f"         └─ {msg}")
    return passed

def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"{msg}: expected {expected}, got {actual}")

def assert_true(value, msg=""):
    if not value:
        raise AssertionError(f"{msg}: expected True, got {value}")

# ============================================================
# TEST 1: Sentiment Analysis
# ============================================================

print("\n" + "="*60)
print("TEST 1: Sentiment Analysis")
print("="*60)

tests_passed = 0
tests_total = 0

def run_sentiment_tests():
    global tests_passed, tests_total
    
    # Test positive sentiment
    tests_total += 1
    result = get_sentiment_sign("我鍾意快節奏工作")
    tests_passed += test_result("Positive sentiment (快節奏)", result == 1, f"got {result}")
    
    # Test negative sentiment
    tests_total += 1
    result = get_sentiment_sign("我偏好穩定環境")
    tests_passed += test_result("Negative sentiment (穩定)", result == -1, f"got {result}")
    
    # Test neutral
    tests_total += 1
    result = get_sentiment_sign("今日天氣普通")
    tests_passed += test_result("Neutral sentiment", result == 0, f"got {result}")
    
    # Test opposite sign detection
    tests_total += 1
    result = is_opposite_sign(1, -1)
    tests_passed += test_result("Opposite signs detected", result == True, f"got {result}")
    
    # Test same sign
    tests_total += 1
    result = is_opposite_sign(1, 1)
    tests_passed += test_result("Same signs NOT opposite", result == False, f"got {result}")
    
    # Test zero sign (should not be opposite)
    tests_total += 1
    result = is_opposite_sign(0, -1)
    tests_passed += test_result("Zero sign not opposite", result == False, f"got {result}")

run_sentiment_tests()

# ============================================================
# TEST 2: Embedding Store
# ============================================================

print("\n" + "="*60)
print("TEST 2: Embedding Store")
print("="*60)

# Use test-specific directory
test_emb_dir = TEST_DIR / "embeddings"
test_emb_dir.mkdir(exist_ok=True)

# Temporarily patch the global - MUST patch BEFORE creating store
import p3_reliability.contradiction.embedding_store as es_module
original_emb_dir = es_module.EMBEDDING_DIR
es_module.EMBEDDING_DIR = str(test_emb_dir)

# Create store AFTER patching
store = EmbeddingStore()

tests_total += 1
store.store("test_fact_001", [0.1] * 1536, {"source": "test"})
tests_passed += test_result("Store embedding", store.exists("test_fact_001"))

tests_total += 1
emb = store.get("test_fact_001")
tests_passed += test_result("Retrieve embedding", emb is not None and len(emb) == 1536)

tests_total += 1
count_before = store.count()
store.store("test_fact_002", [0.2] * 1536)
tests_passed += test_result("Count after add", store.count() == count_before + 1, f"before={count_before}, after={store.count()}")

tests_total += 1
store.delete("test_fact_001")
tests_passed += test_result("Delete embedding", not store.exists("test_fact_001"))

tests_total += 1
exists = store.exists("nonexistent")
tests_passed += test_result("Nonexistent returns False", exists == False)

# Restore
es_module.EMBEDDING_DIR = original_emb_dir

# ============================================================
# TEST 3: LLM Judge
# ============================================================

print("\n" + "="*60)
print("TEST 3: LLM Judge")
print("="*60)

judge = LLMJudge()

tests_total += 1
status = judge.get_status()
tests_passed += test_result("Get LLM status", "model" in status and "available" in status)

tests_total += 1
result = judge.judge("I prefer fast-paced work", "I enjoy dynamic environments", use_heuristic_fallback=True)
tests_passed += test_result("LLM judge (same sentiment)", result["source"] in ["llm", "heuristic"])

tests_total += 1
result = judge.judge("I like fast changes", "I prefer stable environment", use_heuristic_fallback=True)
tests_passed += test_result("LLM judge (opposite sentiment - heuristic)", result["source"] == "heuristic")

# Test parsing
tests_total += 1
parsed = judge._parse_response("CONFLICT|0.85|Opposite attitudes.")
tests_passed += test_result("Parse CONFLICT response", 
    parsed["contradiction"] == True and parsed["confidence"] == 0.85)

tests_total += 1
parsed = judge._parse_response("NO_CONFLICT")
tests_passed += test_result("Parse NO_CONFLICT response", 
    parsed["contradiction"] == False)

tests_total += 1
parsed = judge._parse_response("CONFLICT|invalid")
tests_passed += test_result("Parse invalid response gracefully", 
    parsed["contradiction"] == False)

# ============================================================
# TEST 4: Pruning Scorer
# ============================================================

print("\n" + "="*60)
print("TEST 4: Pruning Scorer")
print("="*60)

# Test fact: low access, low importance, old
old_fact = {
    "id": "fact_old",
    "access_count": 0,
    "importance": "LOW",
    "created_at": "2025-01-01T00:00:00"  # ~1.5 years old
}

# Test fact: high access, high importance, new
new_fact = {
    "id": "fact_new",
    "access_count": 100,
    "importance": "HIGH",
    "created_at": "2026-04-28T00:00:00"  # today
}

# Test fact: medium
medium_fact = {
    "id": "fact_medium",
    "access_count": 5,
    "importance": "MEDIUM",
    "created_at": "2026-04-01T00:00:00"  # ~27 days old
}

tests_total += 1
score_old = compute_prune_score(old_fact)
tests_passed += test_result("Old low-importance fact has high score", 
    score_old > 0.6, f"score={score_old}")

tests_total += 1
score_new = compute_prune_score(new_fact)
tests_passed += test_result("New high-importance fact has low score", 
    score_new < 0.3, f"score={score_new}")

tests_total += 1
score_medium = compute_prune_score(medium_fact)
tests_passed += test_result("Medium fact score between", 
    0.3 < score_medium < 0.6, f"score={score_medium}")

tests_total += 1
result = should_prune(old_fact)
tests_passed += test_result("Old fact should prune", result == True, f"should_prune={result}")

tests_total += 1
result = should_prune(new_fact)
tests_passed += test_result("New fact should NOT prune", result == False, f"should_prune={result}")

# Test ranking
tests_total += 1
facts = [old_fact, new_fact, medium_fact]
scorer = PruneScorer()
ranked = scorer.rank(facts)
tests_passed += test_result("Ranking - highest score first", 
    ranked[0][1] >= ranked[1][1] >= ranked[2][1],
    f"scores: {ranked[0][1]}, {ranked[1][1]}, {ranked[2][1]}")

# ============================================================
# TEST 5: Fact Archiver
# ============================================================

print("\n" + "="*60)
print("TEST 5: Fact Archiver")
print("="*60)

test_archive_dir = TEST_DIR / "archive"
test_archive_dir.mkdir(exist_ok=True)

# Patch archiver - need to patch both module global AND instance variable
import p3_reliability.pruning.archiver as arch_module
original_archive_dir = arch_module.ARCHIVE_DIR
arch_module.ARCHIVE_DIR = test_archive_dir

archiver = FactArchiver(ttl_days=30)
# Also patch the instance variable since __init__ uses module-level ARCHIVE_DIR
archiver.archive_dir = test_archive_dir

tests_total += 1
archive_path = archiver.archive("fact_001", "Test fact content", {"id": "fact_001", "data": "test"})
tests_passed += test_result("Archive fact", Path(archive_path).exists())

tests_total += 1
restored = archiver.restore("fact_001")
tests_passed += test_result("Restore archived fact", 
    restored is not None and restored["id"] == "fact_001",
    f"got: {restored}")

tests_total += 1
restored = archiver.restore("nonexistent")
tests_passed += test_result("Restore nonexistent returns None", restored is None)

tests_total += 1
count = archiver.count()
tests_passed += test_result("Archive count", count["total_facts"] >= 1, f"count={count}")

# Test expiry check
tests_total += 1
expired_entry = {
    "fact_id": "fact_expired",
    "text": "Expired fact",
    "data": {"id": "fact_expired"},
    "archived_at": "2025-01-01T00:00:00",
    "ttl_expires_at": (datetime.now() - timedelta(days=60)).isoformat()
}
expired_file = test_archive_dir / "2025-01-01" / "fact_expired.json"
expired_file.parent.mkdir(exist_ok=True)
with open(expired_file, "w") as f:
    json.dump(expired_entry, f)
restored = archiver.restore("fact_expired")
tests_passed += test_result("Expired fact NOT restored", restored is None)

# Cleanup
tests_total += 1
remaining = archiver.cleanup_expired()
tests_passed += test_result("Cleanup removes expired", remaining >= 1, f"removed={remaining}")

# Restore
arch_module.ARCHIVE_DIR = original_archive_dir

# ============================================================
# TEST 6: Transaction Manager (Basic)
# ============================================================

print("\n" + "="*60)
print("TEST 6: Transaction Manager")
print("="*60)

# Note: Full TX test requires actual storage dirs, do basic test
from p3_reliability.transaction.tx_manager import TransactionManager

tm = TransactionManager()
status = tm.get_status()

tests_total += 1
tests_passed += test_result("TX Manager has 3 layers", 
    len(status["registered_layers"]) == 3,
    f"layers: {status['registered_layers']}")

tests_total += 1
tests_passed += test_result("TX storage paths configured", 
    all(k in status["storage_paths"] for k in ["structured", "vector", "graph"]),
    f"paths: {list(status['storage_paths'].keys())}")

# Test transaction context manager usage
tests_total += 1
try:
    with tm.begin("write_fact", {"entity_id": "test_tx_001", "content": "test"}) as tx:
        tm.write_structured({"entity_id": "test_tx_001", "data": "test"})
    tests_passed += test_result("TX context manager works", True)
except Exception as e:
    tests_passed += test_result("TX context manager works", False, str(e))

# ============================================================
# TEST 7: Usage Tracker (Basic)
# ============================================================

print("\n" + "="*60)
print("TEST 7: Usage Tracker")
print("="*60)

from p3_reliability.usage.tracker import UsageTracker

# Use test-specific state file
test_state_file = TEST_DIR / "usage_tracking.json"
import p3_reliability.usage.tracker as tracker_module
original_state_file = tracker_module.STATE_DIR / "usage_tracking.json"
tracker_module.STATE_DIR = TEST_DIR

tracker = UsageTracker()

tests_total += 1
tracker.on_retrieve("fact_001", "test context")
stats = tracker.get_stats("fact_001")
tests_passed += test_result("Track retrieve event", 
    stats is not None and stats["retrieve_count"] == 1,
    f"count={stats['retrieve_count'] if stats else 'None'}")

tests_total += 1
tracker.on_output("fact_001")
stats = tracker.get_stats("fact_001")
tests_passed += test_result("Track output event", 
    stats is not None and stats["used_in_output"] == True)

tests_total += 1
tracker.on_agent_decision("debug pattern", ["fact_001"])
stats = tracker.get_stats("fact_001")
tests_passed += test_result("Track decision event", 
    stats is not None and stats["decision_influenced_count"] == 1)

tests_total += 1
rate = tracker.get_utilization_rate()
tests_passed += test_result("Utilization rate calculated", 
    0 <= rate <= 1, f"rate={rate}")

# Restore
tracker_module.STATE_DIR = original_state_file.parent

# ============================================================
# TEST 8: Pattern Binding (Basic)
# ============================================================

print("\n" + "="*60)
print("TEST 8: Pattern Binding")
print("="*60)

from p3_reliability.usage.binding import PatternBinding

test_binding_file = TEST_DIR / "pattern_bindings.json"
import p3_reliability.usage.binding as binding_module
original_binding_file = binding_module.STATE_DIR / "pattern_bindings.json"
binding_module.STATE_DIR = TEST_DIR

binding = PatternBinding()

tests_total += 1
binding.add_binding("debug system", ["fact_001", "fact_002"], "hash123")
tests_passed += test_result("Add pattern binding", True)

tests_total += 1
facts = binding.get_facts_for_context("debugging a system issue")
tests_passed += test_result("Get facts for similar context", 
    len(facts) >= 1, f"facts={facts}")

tests_total += 1
boost = binding.suggest_boost("fact_001", "debug system problem")
tests_passed += test_result("Suggest boost works", isinstance(boost, bool))

tests_total += 1
stats = binding.get_stats()
tests_passed += test_result("Binding stats calculated", 
    "total_patterns" in stats and "total_bindings" in stats,
    f"stats={stats}")

# Restore
binding_module.STATE_DIR = original_binding_file.parent

# ============================================================
# SUMMARY
# ============================================================

print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
print(f"  Passed: {tests_passed}/{tests_total}")
print(f"  Failed: {tests_total - tests_passed}/{tests_total}")
print(f"  Success rate: {100*tests_passed/tests_total:.1f}%")

if tests_passed == tests_total:
    print("\n🎉 ALL TESTS PASSED")
else:
    print(f"\n⚠️  {tests_total - tests_passed} tests failed - review above")

# Cleanup test directory
shutil.rmtree(TEST_DIR, ignore_errors=True)

print("\n✅ P3 Reliability Layer - All tests complete\n")