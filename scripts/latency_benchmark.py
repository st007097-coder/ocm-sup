#!/usr/bin/env python3
"""
OCM-Sup Latency Benchmark
=========================

Measures search latency for OCM-Sup Triple-Stream Search.

Tests:
1. Cold start latency (first query after init)
2. Warm query latency (subsequent queries)
3. P50/P95/P99 latencies
4. Query expansion latency
5. Cross-lingual query latency

Usage:
    python3 latency_benchmark.py [--runs N]
"""

import sys
import json
import time
import statistics
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/OCM-Sup/scripts')
from triple_stream_search import TripleStreamSearch

WIKI_PATH = '/root/.openclaw/workspace/wiki'

# Test queries
QUERIES = [
    'hermes',
    '古洞站',
    '期哥',
    'OpenClaw',
    '阿星',
    'OCM Sup',
    'BM25',
    'Triple-Stream',
    'RRF',
    'Query Expansion',
    'knowledge graph',
    'vector search',
    'quantity surveyor',
    '香港',
    '工程',
]

def measure_latency(search, query, top_k=5):
    """Measure latency for a single query"""
    start = time.perf_counter()
    results = search.search(query, top_k=top_k)
    end = time.perf_counter()
    latency_ms = (end - start) * 1000
    return latency_ms, len(results)


def run_benchmark(runs=3):
    """Run latency benchmark"""
    print("=" * 60)
    print("OCM-SUP LATENCY BENCHMARK")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Runs per query: {runs}")
    print()
    
    # Initialize search
    print("Initializing Triple-Stream Search...")
    init_start = time.perf_counter()
    search = TripleStreamSearch(wiki_path=WIKI_PATH)
    init_end = time.perf_counter()
    init_time = (init_end - init_start) * 1000
    print(f"✅ Init time: {init_time:.0f}ms")
    print()
    
    # Cold start measurement (first query)
    print("Measuring cold start latency...")
    cold_latencies = []
    cold_start = time.perf_counter()
    results = search.search('hermes', top_k=5)
    cold_end = time.perf_counter()
    cold_latency = (cold_end - cold_start) * 1000
    cold_latencies.append(cold_latency)
    print(f"  Cold start: {cold_latency:.1f}ms ({len(results)} results)")
    print()
    
    # Warm query latencies
    print("Measuring warm query latencies...")
    all_latencies = []
    per_query_latencies = {q: [] for q in QUERIES}
    
    for run in range(runs):
        print(f"\n--- Run {run + 1}/{runs} ---")
        for query in QUERIES:
            latency, num_results = measure_latency(search, query)
            all_latencies.append(latency)
            per_query_latencies[query].append(latency)
            
            # Print first run details
            if run == 0:
                print(f"  {query:<25}: {latency:>8.1f}ms ({num_results} results)")
    
    # Calculate statistics
    print()
    print("=" * 60)
    print("LATENCY RESULTS")
    print("=" * 60)
    print()
    
    sorted_latencies = sorted(all_latencies)
    n = len(sorted_latencies)
    
    p50_idx = int(n * 0.50)
    p95_idx = int(n * 0.95)
    p99_idx = int(n * 0.99)
    
    p50 = sorted_latencies[p50_idx]
    p95 = sorted_latencies[p95_idx]
    p99 = sorted_latencies[p99_idx]
    
    mean = statistics.mean(all_latencies)
    median = statistics.median(all_latencies)
    stdev = statistics.stdev(all_latencies) if len(all_latencies) > 1 else 0
    
    print(f"Cold Start:      {cold_latency:.1f}ms")
    print()
    print(f"Overall ({len(all_latencies)} samples):")
    print(f"  Mean:          {mean:.1f}ms")
    print(f"  Median:        {median:.1f}ms")
    print(f"  Std Dev:       {stdev:.1f}ms")
    print(f"  Min:           {min(all_latencies):.1f}ms")
    print(f"  Max:           {max(all_latencies):.1f}ms")
    print(f"  P50:           {p50:.1f}ms")
    print(f"  P95:           {p95:.1f}ms")
    print(f"  P99:           {p99:.1f}ms")
    print()
    
    # Per-query breakdown
    print("Per-Query Latency (first run):")
    print("-" * 60)
    for query in QUERIES:
        latencies = per_query_latencies[query]
        avg = statistics.mean(latencies)
        print(f"  {query:<25}: {avg:>8.1f}ms")
    
    print()
    
    # Performance assessment
    print("=" * 60)
    print("PERFORMANCE ASSESSMENT")
    print("=" * 60)
    
    if p99 < 100:
        rating = "🟢 Excellent"
        comment = "P99 < 100ms - Excellent for all use cases"
    elif p99 < 500:
        rating = "🟡 Good"
        comment = "P99 < 500ms - Good for interactive use"
    elif p99 < 1000:
        rating = "🟠 Fair"
        comment = "P99 < 1s - Acceptable for background tasks"
    else:
        rating = "🔴 Slow"
        comment = "P99 > 1s - Needs optimization"
    
    print(f"Rating: {rating}")
    print(f"Comment: {comment}")
    
    print()
    
    return {
        'init_time_ms': init_time,
        'cold_start_ms': cold_latency,
        'mean_ms': mean,
        'median_ms': median,
        'p50_ms': p50,
        'p95_ms': p95,
        'p99_ms': p99,
        'min_ms': min(all_latencies),
        'max_ms': max(all_latencies),
        'rating': rating,
    }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OCM-Sup Latency Benchmark")
    parser.add_argument('--runs', type=int, default=3, help='Number of runs per query')
    args = parser.parse_args()
    
    results = run_benchmark(runs=args.runs)
    
    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
