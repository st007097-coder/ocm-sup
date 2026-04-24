#!/usr/bin/env python3
"""
OCM-Sup Continuity Layer Benchmark
===================================

Tests the performance of the continuity layer.

Measures:
1. Message classification latency
2. Carryover retrieval latency
3. Hook lifecycle performance
4. Frontstage guard sanitization speed
5. Memory trace write speed

Usage:
    python3 continuity_benchmark.py [--iterations N]
"""

import sys
import time
import statistics
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/OCM-Sup/scripts')

from continuity.continuity_state import ContinuityState
from continuity.hook_lifecycle import HookLifecycle
from continuity.frontstage_guard import FrontstageGuard
from continuity.daily_memory_trace import DailyMemoryTrace


def benchmark_classification(iterations=100):
    """Benchmark message classification"""
    print("=" * 60)
    print("1. Message Classification Benchmark")
    print("=" * 60)
    
    state = ContinuityState()
    
    test_messages = [
        "你好嗎？",
        "幫我記住我哋研究緊OCM Sup融合方案",
        "麻煩你幫我跟進古洞站項目進度",
        "我感覺有啲攰",
        "呢個係私人資料，保密",
        "我哋之前研究緊融合方案，繼續傾",
    ]
    
    latencies = []
    
    for _ in range(iterations):
        for msg in test_messages:
            start = time.perf_counter()
            state.handle_message(msg)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
    
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    
    print(f"Iterations: {iterations} x {len(test_messages)} = {len(latencies)} total")
    print(f"Mean:   {statistics.mean(latencies):.3f}ms")
    print(f"Median: {statistics.median(latencies):.3f}ms")
    print(f"P95:    {sorted_lat[int(n * 0.95)]:.3f}ms")
    print(f"P99:    {sorted_lat[int(n * 0.99)]:.3f}ms")
    print(f"Max:    {max(latencies):.3f}ms")
    
    return latencies


def benchmark_carryover(iterations=100):
    """Benchmark carryover operations"""
    print()
    print("=" * 60)
    print("2. Carryover Benchmark")
    print("=" * 60)
    
    state = ContinuityState()
    
    # Setup: create a pending topic
    state.handle_message("幫我記住我哋研究緊OCM Sup")
    
    # Benchmark get_pending_topic
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        state.carryover.get_pending_topic()
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
    
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    
    print(f"Iterations: {iterations}")
    print(f"Mean:   {statistics.mean(latencies):.3f}ms")
    print(f"Median: {statistics.median(latencies):.3f}ms")
    print(f"P95:    {sorted_lat[int(n * 0.95)]:.3f}ms")
    print(f"P99:    {sorted_lat[int(n * 0.99)]:.3f}ms")
    print(f"Max:    {max(latencies):.3f}ms")
    
    return latencies


def benchmark_hook_lifecycle(iterations=50):
    """Benchmark hook lifecycle operations"""
    print()
    print("=" * 60)
    print("3. Hook Lifecycle Benchmark")
    print("=" * 60)
    
    lifecycle = HookLifecycle()
    
    # Benchmark create_hook
    create_latencies = []
    hook_ids = []
    
    for i in range(iterations):
        start = time.perf_counter()
        hook_id = lifecycle.create_hook(
            incident_id=f"test_incident_{i}",
            entity_name=f"Test Topic {i}",
            event_type="delegated_task",
            followup_focus=f"Follow up on topic {i}",
            causal_memory={"facts": [f"test fact {i}"]}
        )
        latency = (time.perf_counter() - start) * 1000
        create_latencies.append(latency)
        hook_ids.append(hook_id)
    
    # Benchmark check_due_hooks
    due_latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        lifecycle.check_due_hooks()
        latency = (time.perf_counter() - start) * 1000
        due_latencies.append(latency)
    
    # Benchmark render_followup
    render_latencies = []
    for hook_id in hook_ids[:iterations // 2]:
        start = time.perf_counter()
        lifecycle.render_followup(hook_id)
        latency = (time.perf_counter() - start) * 1000
        render_latencies.append(latency)
    
    print(f"Create Hook ({iterations} iterations):")
    print(f"  Mean:   {statistics.mean(create_latencies):.3f}ms")
    print(f"  Median: {statistics.median(create_latencies):.3f}ms")
    print(f"  Max:    {max(create_latencies):.3f}ms")
    print()
    
    print(f"Check Due Hooks ({iterations} iterations):")
    print(f"  Mean:   {statistics.mean(due_latencies):.3f}ms")
    print(f"  Median: {statistics.median(due_latencies):.3f}ms")
    print(f"  Max:    {max(due_latencies):.3f}ms")
    print()
    
    print(f"Render Followup ({len(render_latencies)} iterations):")
    print(f"  Mean:   {statistics.mean(render_latencies):.3f}ms")
    print(f"  Median: {statistics.median(render_latencies):.3f}ms")
    print(f"  Max:    {max(render_latencies):.3f}ms")
    
    return {
        'create': create_latencies,
        'check_due': due_latencies,
        'render': render_latencies,
    }


def benchmark_frontstage_guard(iterations=100):
    """Benchmark frontstage guard sanitization"""
    print()
    print("=" * 60)
    print("4. Frontstage Guard Benchmark")
    print("=" * 60)
    
    guard = FrontstageGuard()
    
    test_messages = [
        "你好嗎？想傾乜？",
        "你之前提到嘅古洞站項目進度點樣？",
        "想提醒你之前交代嘅任務（上次傾呢個係 2026-04-24T14:00:00.123456）",
        "你之前提到 hook_12345678，想繼續傾嗎？",
        "✅ 正常自然嘅跟進：你之前話想研究 OCM Sup 融合，準備好繼續未？",
    ]
    
    latencies = []
    safe_checks = []
    
    for _ in range(iterations):
        for msg in test_messages:
            # is_safe
            start = time.perf_counter()
            is_safe = guard.is_safe(msg)
            latency = (time.perf_counter() - start) * 1000
            safe_checks.append((is_safe, latency))
            
            # sanitize
            if not is_safe:
                start = time.perf_counter()
                guard.sanitize(msg)
                latency = (time.perf_counter() - start) * 1000
                latencies.append(latency)
    
    unsafe_count = len(latencies)
    total_checks = len(safe_checks)
    
    print(f"Total is_safe checks: {total_checks}")
    print(f"Unsafe (sanitized):   {unsafe_count}")
    print()
    
    print(f"Sanitize ({unsafe_count} iterations):")
    print(f"  Mean:   {statistics.mean(latencies):.3f}ms")
    print(f"  Median: {statistics.median(latencies):.3f}ms")
    print(f"  Max:    {max(latencies):.3f}ms")
    
    return latencies


def benchmark_memory_trace(iterations=100):
    """Benchmark memory trace operations"""
    print()
    print("=" * 60)
    print("5. Memory Trace Benchmark")
    print("=" * 60)
    
    trace = DailyMemoryTrace()
    
    latencies = []
    
    for i in range(iterations):
        start = time.perf_counter()
        trace.write(
            event_type="parked_topic",
            action="created",
            entity_name=f"Benchmark Topic {i}",
            topic_id=f"bench_{i}",
            causal_memory={"facts": [f"fact {i}"]},
            severity="info"
        )
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
    
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    
    print(f"Iterations: {iterations}")
    print(f"Mean:   {statistics.mean(latencies):.3f}ms")
    print(f"Median: {statistics.median(latencies):.3f}ms")
    print(f"P95:    {sorted_lat[int(n * 0.95)]:.3f}ms")
    print(f"P99:    {sorted_lat[int(n * 0.99)]:.3f}ms")
    print(f"Max:    {max(latencies):.3f}ms")
    
    return latencies


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OCM-Sup Continuity Layer Benchmark")
    parser.add_argument('--iterations', type=int, default=100, help='Number of iterations')
    args = parser.parse_args()
    
    print()
    print("=" * 60)
    print("OCM-SUP CONTINUITY LAYER BENCHMARK")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Iterations per test: {args.iterations}")
    print()
    
    # Run benchmarks
    class_latencies = benchmark_classification(args.iterations)
    carryover_latencies = benchmark_carryover(args.iterations)
    hook_results = benchmark_hook_lifecycle(args.iterations // 2)
    guard_latencies = benchmark_frontstage_guard(args.iterations)
    trace_latencies = benchmark_memory_trace(args.iterations)
    
    # Summary
    print()
    print("=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print()
    print(f"Message Classification: {statistics.mean(class_latencies):.3f}ms avg")
    print(f"Carryover Retrieval:    {statistics.mean(carryover_latencies):.3f}ms avg")
    print(f"Hook Create:           {statistics.mean(hook_results['create']):.3f}ms avg")
    print(f"Hook Check Due:         {statistics.mean(hook_results['check_due']):.3f}ms avg")
    print(f"Hook Render:            {statistics.mean(hook_results['render']):.3f}ms avg")
    print(f"Frontstage Sanitize:    {statistics.mean(guard_latencies):.3f}ms avg")
    print(f"Memory Trace Write:     {statistics.mean(trace_latencies):.3f}ms avg")
    print()
    
    # Performance assessment
    all_latencies = (
        class_latencies + 
        carryover_latencies + 
        hook_results['create'] + 
        hook_results['check_due'] + 
        hook_results['render'] + 
        guard_latencies + 
        trace_latencies
    )
    
    overall_mean = statistics.mean(all_latencies)
    
    if overall_mean < 10:
        rating = "🟢 Excellent"
        comment = "All operations sub-10ms - very fast"
    elif overall_mean < 50:
        rating = "🟡 Good"
        comment = "All operations under 50ms - acceptable"
    elif overall_mean < 100:
        rating = "🟠 Fair"
        comment = "Some operations over 100ms - needs attention"
    else:
        rating = "🔴 Slow"
        comment = "Operations too slow - needs optimization"
    
    print(f"Overall Mean: {overall_mean:.3f}ms")
    print(f"Rating: {rating}")
    print(f"Comment: {comment}")
    
    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
