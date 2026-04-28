#!/usr/bin/env python3
"""
OCM Sup v3 - Comprehensive System Test & Benchmark

Usage:
    python3 tests/comprehensive_test.py
    python3 tests/comprehensive_test.py --verbose
    python3 tests/comprehensive_test.py --benchmark-only
"""

import sys
import time
import argparse
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================
# CONFIGURATION
# ============================================================

CLEAR_CACHES = True  # Clear before test for clean benchmark
BATCH_SIZE = 15  # Number of writes for latency test
WARMUP_WRITES = 5  # Warmup writes before benchmark

# ============================================================
# TEST MODULES
# ============================================================

def clear_caches():
    """Clear all caches for clean test."""
    from hybrid_layer.idempotency_guard import clear as clear_idem
    from hybrid_layer.embedding_cache import clear as clear_cache
    from hybrid_layer.vector_batcher import force_flush
    clear_idem()
    clear_cache()
    force_flush()

def test_memory_reliability_layer():
    """
    TEST 1: Memory Reliability Layer (v2.6)
    
    Tests core reliability components:
    - TransactionManager (atomic writes + rollback)
    - UsageTracker (usage tracking)
    - HealthMetrics (system health)
    """
    print('\n' + '=' * 60)
    print('TEST 1: Memory Reliability Layer (v2.6)')
    print('=' * 60)
    
    from memory_reliability_layer import (
        TransactionManager,
        ContradictionEngine,
        UsageTracker,
        AdaptivePruning,
        HealthMetrics
    )
    
    results = {'passed': 0, 'failed': 0, 'tests': []}
    
    # Test 1.1: TransactionManager
    print('\n[1.1] TransactionManager...')
    try:
        tx = TransactionManager()
        test_memory = {
            'entity_id': 'test_tx_001',
            'type': 'test',
            'subject': 'Benchmark Test',
            'action': 'Testing transaction manager'
        }
        with tx.begin('test_write', test_memory) as t:
            tx.write_structured(t, test_memory)
        print('  ✓ Transaction commit: PASS')
        results['passed'] += 1
        results['tests'].append({'name': 'TransactionManager', 'status': 'PASS'})
    except Exception as e:
        print(f'  ✗ Transaction failed: {e}')
        results['failed'] += 1
        results['tests'].append({'name': 'TransactionManager', 'status': 'FAIL', 'error': str(e)})
    
    # Test 1.2: UsageTracker
    print('\n[1.2] UsageTracker...')
    try:
        tracker = UsageTracker()
        tracker.on_retrieve('test_fact', context='benchmark')
        tracker.on_output('test_fact')
        stats = tracker.get_stats('test_fact')
        if stats and stats['retrieve_count'] == 1 and stats['used_in_output']:
            print('  ✓ Usage tracking: PASS')
            results['passed'] += 1
            results['tests'].append({'name': 'UsageTracker', 'status': 'PASS'})
        else:
            raise Exception(f'Stats incorrect: {stats}')
    except Exception as e:
        print(f'  ✗ Usage tracking failed: {e}')
        results['failed'] += 1
        results['tests'].append({'name': 'UsageTracker', 'status': 'FAIL', 'error': str(e)})
    
    # Test 1.3: HealthMetrics
    print('\n[1.3] HealthMetrics...')
    try:
        metrics = HealthMetrics()
        report = metrics.compute()
        print(f'  Health Score: {report.health_score:.2%}')
        print(f'  Total Facts: {report.total_facts}')
        if report.health_score > 0:
            print('  ✓ Health metrics: PASS')
            results['passed'] += 1
            results['tests'].append({'name': 'HealthMetrics', 'status': 'PASS', 'score': report.health_score})
        else:
            raise Exception('Health score is 0')
    except Exception as e:
        print(f'  ✗ Health metrics failed: {e}')
        results['failed'] += 1
        results['tests'].append({'name': 'HealthMetrics', 'status': 'FAIL', 'error': str(e)})
    
    print(f'\n[TEST 1] Result: {results["passed"]}/{results["passed"]+results["failed"]} PASSED')
    return results

def test_hybrid_layer():
    """
    TEST 2: Hybrid Layer (v3) - Reliability
    
    Tests reliability components:
    - Idempotency Guard (prevent duplicate writes)
    - Retry Utility (exponential backoff retry)
    """
    print('\n' + '=' * 60)
    print('TEST 2: Hybrid Layer (v3) - Reliability')
    print('=' * 60)
    
    from hybrid_layer import is_duplicate, retry
    
    results = {'passed': 0, 'failed': 0, 'tests': []}
    
    # Test 2.1: Idempotency Guard
    print('\n[2.1] Idempotency Guard...')
    try:
        from hybrid_layer.idempotency_guard import clear as clear_idem
        clear_idem()
        
        test_mem = {'subject': 'Test', 'action': 'Idempotency Check'}
        result1 = is_duplicate(test_mem)  # First should be False
        result2 = is_duplicate(test_mem)  # Second should be True
        
        if not result1 and result2:
            print('  ✓ First write: allowed')
            print('  ✓ Second write: blocked as duplicate')
            print('  ✓ Idempotency: PASS')
            results['passed'] += 1
            results['tests'].append({'name': 'IdempotencyGuard', 'status': 'PASS'})
        else:
            raise Exception(f'Results incorrect: {result1}, {result2}')
    except Exception as e:
        print(f'  ✗ Idempotency failed: {e}')
        results['failed'] += 1
        results['tests'].append({'name': 'IdempotencyGuard', 'status': 'FAIL', 'error': str(e)})
    
    # Test 2.2: Retry Utility
    print('\n[2.2] Retry Utility...')
    try:
        call_count = [0]
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception('Simulated failure')
            return 'success'
        
        result = retry(flaky_function, retries=3, delay=0.01)
        if result == 'success' and call_count[0] == 3:
            print(f'  ✓ Retry worked: {call_count[0]} attempts')
            print('  ✓ Retry utility: PASS')
            results['passed'] += 1
            results['tests'].append({'name': 'RetryUtility', 'status': 'PASS', 'attempts': 3})
        else:
            raise Exception(f'Result: {result}, attempts: {call_count[0]}')
    except Exception as e:
        print(f'  ✗ Retry failed: {e}')
        results['failed'] += 1
        results['tests'].append({'name': 'RetryUtility', 'status': 'FAIL', 'error': str(e)})
    
    print(f'\n[TEST 2] Result: {results["passed"]}/{results["passed"]+results["failed"]} PASSED')
    return results

def test_integration():
    """
    TEST 3: Integration - memory_tx_sync.py
    
    Tests:
    - Idempotency in write path
    - Vector batching (async)
    """
    print('\n' + '=' * 60)
    print('TEST 3: Integration - memory_tx_sync.py')
    print('=' * 60)
    
    from scripts.memory_tx_sync import MemoryTransactionSync
    from hybrid_layer.vector_batcher import get_buffer_size
    
    results = {'passed': 0, 'failed': 0, 'tests': [], 'benchmark': {}}
    
    tx_sync = MemoryTransactionSync()
    
    # Test 3.1: Idempotency in write
    print('\n[3.1] Idempotency in write...')
    try:
        mem1 = {
            'type': 'fact',
            'subject': 'Integration Test',
            'action': 'Testing write path'
        }
        s1, m1 = tx_sync.write(mem1)
        s2, m2 = tx_sync.write(mem1)  # Duplicate
        
        if s1 and not s2 and 'DUPLICATE' in m2:
            print('  ✓ First write: success')
            print('  ✓ Duplicate write: blocked')
            print('  ✓ Idempotency integration: PASS')
            results['passed'] += 1
            results['tests'].append({'name': 'IdempotencyIntegration', 'status': 'PASS'})
        else:
            raise Exception(f'Failed: {s1}, {m1}, {s2}, {m2}')
    except Exception as e:
        print(f'  ✗ Failed: {e}')
        results['failed'] += 1
        results['tests'].append({'name': 'IdempotencyIntegration', 'status': 'FAIL', 'error': str(e)})
    
    # Test 3.2: Vector Batching
    print('\n[3.2] Vector Batching...')
    try:
        memories = [
            {'type': 'fact', 'subject': f'Batch {i}', 'action': f'Test {i}'}
            for i in range(BATCH_SIZE)
        ]
        
        start = time.time()
        for m in memories:
            tx_sync.write(m)
        elapsed = time.time() - start
        
        buffer_size = get_buffer_size()
        avg_latency = (elapsed * 1000) / BATCH_SIZE
        
        print(f'  ✓ {BATCH_SIZE} writes completed in {elapsed*1000:.1f}ms')
        print(f'  ✓ Average latency: {avg_latency:.2f}ms per write')
        print(f'  ✓ Buffer size: {buffer_size}')
        print('  ✓ Vector batching: PASS')
        
        results['passed'] += 1
        results['tests'].append({'name': 'VectorBatching', 'status': 'PASS'})
        results['benchmark']['latency_avg_ms'] = avg_latency
        results['benchmark']['latency_total_ms'] = elapsed * 1000
        results['benchmark']['batch_writes'] = BATCH_SIZE
    except Exception as e:
        print(f'  ✗ Failed: {e}')
        results['failed'] += 1
        results['tests'].append({'name': 'VectorBatching', 'status': 'FAIL', 'error': str(e)})
    
    print(f'\n[TEST 3] Result: {results["passed"]}/{results["passed"]+results["failed"]} PASSED')
    return results

def test_postprocessing():
    """
    TEST 4: Post-processing
    
    Tests:
    - Contradiction check (async)
    - Adaptive pruning (async)
    - Health metrics computation
    """
    print('\n' + '=' * 60)
    print('TEST 4: Post-processing')
    print('=' * 60)
    
    from hybrid_layer.postprocess_worker import run_postprocess_sync
    
    results = {'passed': 0, 'failed': 0, 'tests': [], 'metrics': {}}
    
    print('\n[4.1] Sync post-processing...')
    try:
        results_sync = run_postprocess_sync(contradiction=True, pruning=True, metrics=True)
        
        metrics_result = results_sync.get('metrics')
        if metrics_result:
            print(f'  ✓ Health score: {metrics_result.health_score:.2%}')
            print(f'  ✓ Total facts: {metrics_result.total_facts}')
            print('  ✓ Post-processing: PASS')
            
            results['passed'] += 1
            results['tests'].append({'name': 'PostProcessing', 'status': 'PASS'})
            results['metrics']['health_score'] = metrics_result.health_score
            results['metrics']['total_facts'] = metrics_result.total_facts
        else:
            raise Exception('No metrics result')
    except Exception as e:
        print(f'  ✗ Post-processing failed: {e}')
        results['failed'] += 1
        results['tests'].append({'name': 'PostProcessing', 'status': 'FAIL', 'error': str(e)})
    
    print(f'\n[TEST 4] Result: {results["passed"]}/{results["passed"]+results["failed"]} PASSED')
    return results

def run_benchmark():
    """
    Run benchmark tests with warmup.
    """
    print('\n' + '=' * 60)
    print('BENCHMARK: Latency Test with Warmup')
    print('=' * 60)
    
    from scripts.memory_tx_sync import MemoryTransactionSync
    from hybrid_layer.embedding_cache import get_stats
    from hybrid_layer.vector_batcher import force_flush, get_buffer_size
    
    tx_sync = MemoryTransactionSync()
    
    # Warmup
    print(f'\n[WARMUP] Running {WARMUP_WRITES} warmup writes...')
    warmup_memories = [
        {'type': 'fact', 'subject': f'Warmup {i}', 'action': f'Warm {i}'}
        for i in range(WARMUP_WRITES)
    ]
    for m in warmup_memories:
        tx_sync.write(m)
    force_flush()
    print('  ✓ Warmup complete')
    
    # Benchmark
    print(f'\n[BENCHMARK] Running {BATCH_SIZE} writes for latency test...')
    benchmark_memories = [
        {'type': 'fact', 'subject': f'Benchmark {i}', 'action': f'Test {i}'}
        for i in range(BATCH_SIZE)
    ]
    
    start = time.time()
    for m in benchmark_memories:
        tx_sync.write(m)
    elapsed = time.time() - start
    
    # Force flush to complete all writes
    force_flush()
    
    # Get stats
    buffer_size = get_buffer_size()
    cache_stats = get_stats()
    
    print(f'\n[RESULTS]')
    print(f'  Total time: {elapsed*1000:.2f}ms')
    print(f'  Average latency: {(elapsed*1000)/BATCH_SIZE:.2f}ms per write')
    print(f'  Buffer remaining: {buffer_size}')
    print(f'  Cache entries: {cache_stats["disk_entries"]}')
    
    return {
        'total_ms': elapsed * 1000,
        'avg_ms': (elapsed * 1000) / BATCH_SIZE,
        'batch_size': BATCH_SIZE,
        'buffer_size': buffer_size,
        'cache_entries': cache_stats['disk_entries']
    }

def print_summary(all_results, benchmark_results):
    """Print final summary."""
    print('\n' + '=' * 60)
    print('FINAL SUMMARY')
    print('=' * 60)
    
    total_passed = 0
    total_failed = 0
    
    for result in all_results:
        total_passed += result['passed']
        total_failed += result['failed']
    
    print(f'\nTests Passed: {total_passed}/{total_passed + total_failed}')
    print(f'Failed: {total_failed}')
    
    print(f'\n[BENCHMARK RESULTS]')
    print(f'  Write Latency (avg): {benchmark_results["avg_ms"]:.2f}ms')
    print(f'  Cache Entries: {benchmark_results["cache_entries"]}')
    print(f'  Buffer Size: {benchmark_results["buffer_size"]}')
    
    if total_failed == 0:
        print('\n' + '=' * 60)
        print('🎉 ALL TESTS PASSED!')
        print('=' * 60)
    else:
        print('\n' + '=' * 60)
        print(f'⚠️  {total_failed} TESTS FAILED')
        print('=' * 60)

def main():
    parser = argparse.ArgumentParser(description='OCM Sup v3 Comprehensive Test')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--benchmark-only', '-b', action='store_true', help='Run benchmark only')
    args = parser.parse_args()
    
    print('=' * 60)
    print('OCM Sup v3 - Comprehensive System Test')
    print('=' * 60)
    
    # Clear caches if configured
    if CLEAR_CACHES:
        print('\n[SETUP] Clearing caches for clean test...')
        clear_caches()
        print('  ✓ Caches cleared\n')
    
    all_results = []
    
    # Run tests
    if not args.benchmark_only:
        result1 = test_memory_reliability_layer()
        result2 = test_hybrid_layer()
        result3 = test_integration()
        result4 = test_postprocessing()
        all_results = [result1, result2, result3, result4]
    
    # Run benchmark
    benchmark_results = run_benchmark()
    
    # Print summary
    print_summary(all_results, benchmark_results)

if __name__ == '__main__':
    main()