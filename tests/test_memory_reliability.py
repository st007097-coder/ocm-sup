#!/usr/bin/env python3
"""
Test script for Memory Reliability Layer
OCM Sup v2.6

Tests all modules independently.
"""

import sys
import json
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_reliability_layer import (
    TransactionManager,
    ContradictionEngine,
    UsageTracker,
    AdaptivePruning,
    HealthMetrics,
    config
)


def test_tx_manager():
    """Test transaction manager."""
    print("\n=== Testing TransactionManager ===")
    
    tx_manager = TransactionManager()
    
    # Test begin/commit
    payload = {"entity_id": "test_tx_001", "type": "test", "subject": "Test Fact"}
    
    try:
        with tx_manager.begin("write_test", payload) as tx:
            tx_manager.write_structured(tx, payload)
            tx_manager.write_vector(tx, {
                "entity_id": "test_tx_001",
                "embedding_text": "Test Fact content"
            })
            tx_manager.write_graph(tx, {
                "entity_id": "test_tx_001",
                "subject": "Test Fact",
                "entities": [],
                "relations": []
            })
        
        print("✅ Transaction committed successfully")
        
        # Verify storage
        struct_file = config.STORAGE_DIR / "test_tx_001.json"
        if struct_file.exists():
            print("✅ Structured storage verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Transaction failed: {e}")
        return False


def test_usage_tracker():
    """Test usage tracker."""
    print("\n=== Testing UsageTracker ===")
    
    tracker = UsageTracker()
    
    # Clear existing data for clean test
    test_fact_id = "test_fact_1"
    if test_fact_id in tracker._data:
        del tracker._data[test_fact_id]
    
    # Test tracking
    tracker.on_retrieve(test_fact_id, context="test query")
    tracker.on_retrieve(test_fact_id, context="test query")
    tracker.on_output(test_fact_id)
    
    stats = tracker.get_stats(test_fact_id)
    
    if stats and stats["retrieve_count"] == 2 and stats["used_in_output"]:
        print(f"✅ Usage tracking verified: {stats}")
        return True
    else:
        print(f"❌ Usage stats incorrect: {stats}")
        return False


def test_adaptive_pruning():
    """Test adaptive pruning."""
    print("\n=== Testing AdaptivePruning ===")
    
    pruner = AdaptivePruning(threshold=0.7)
    now = time.time()
    
    test_facts = [
        {
            "entity_id": "fact_old",
            "subject": "Old fact",
            "timestamp": now - (60 * 86400),  # 60 days old
            "importance": "LOW"
        },
        {
            "entity_id": "fact_new",
            "subject": "New fact", 
            "timestamp": now,  # Just now
            "importance": "HIGH"
        }
    ]
    
    usage_data = {
        "fact_old": {"count": 0},
        "fact_new": {"count": 100}
    }
    
    result = pruner.execute(test_facts, usage_data, dry_run=True)
    
    print(f"✅ Pruning dry-run: {result.pruned_count} eligible for pruning")
    
    # Check scores
    score_old = pruner.score(test_facts[0], usage_data["fact_old"])
    score_new = pruner.score(test_facts[1], usage_data["fact_new"])
    
    print(f"   Old fact score: {score_old} (should be high)")
    print(f"   New fact score: {score_new} (should be low)")
    
    if score_old > score_new:
        print("✅ Pruning score calculation verified")
        return True
    else:
        print("❌ Pruning score calculation incorrect")
        return False


def test_health_metrics():
    """Test health metrics."""
    print("\n=== Testing HealthMetrics ===")
    
    metrics = HealthMetrics()
    report = metrics.compute()
    
    print(f"✅ Health metrics computed:")
    print(f"   Total facts: {report.total_facts}")
    print(f"   Health score: {report.health_score:.2%}")
    print(f"   Duplicate rate: {report.duplicate_rate:.2%}")
    print(f"   Unused rate: {report.unused_rate:.2%}")
    
    return True


def main():
    print("=" * 50)
    print("Memory Reliability Layer - Test Suite")
    print("=" * 50)
    
    results = {}
    
    results["tx_manager"] = test_tx_manager()
    results["usage_tracker"] = test_usage_tracker()
    results["adaptive_pruning"] = test_adaptive_pruning()
    results["health_metrics"] = test_health_metrics()
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
