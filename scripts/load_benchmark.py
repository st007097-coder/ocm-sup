#!/usr/bin/env python3
"""
OCM-Sup Load Benchmark
======================

Tests concurrent query performance and throughput.

Measures:
1. Sequential throughput (queries/second)
2. Concurrent query handling
3. Sustained load performance
4. Recovery after high load

Usage:
    python3 load_benchmark.py [--concurrency N] [--duration S]
"""

import sys
import time
import threading
import statistics
from datetime import datetime
from pathlib import Path
from collections import defaultdict

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
]

# Shared state
results_lock = threading.Lock()
latencies = []
errors = []
throughput_count = 0
stop_flag = threading.Event()


def query_worker(search, query, thread_id, duration):
    """Worker thread that runs queries for a duration"""
    global latencies, errors, throughput_count
    
    end_time = time.time() + duration
    local_count = 0
    
    while not stop_flag.is_set() and time.time() < end_time:
        start = time.perf_counter()
        try:
            results = search.search(query, top_k=5)
            latency = (time.perf_counter() - start) * 1000
            
            with results_lock:
                latencies.append(latency)
                throughput_count += 1
                local_count += 1
        except Exception as e:
            with results_lock:
                errors.append(str(e))


def run_load_test(concurrency=5, duration=10):
    """Run load test with concurrent queries"""
    global latencies, errors, throughput_count, stop_flag
    
    print("=" * 60)
    print("OCM-SUP LOAD BENCHMARK")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Concurrency: {concurrency}")
    print(f"Duration: {duration}s per query")
    print()
    
    # Initialize search
    print("Initializing Triple-Stream Search...")
    init_start = time.perf_counter()
    search = TripleStreamSearch(wiki_path=WIKI_PATH)
    init_time = (time.perf_counter() - init_start) * 1000
    print(f"✅ Init time: {init_time:.0f}ms")
    print()
    
    # Reset counters
    latencies = []
    errors = []
    throughput_count = 0
    stop_flag = threading.Event()
    
    # Sequential baseline
    print("--- Sequential Baseline (single thread) ---")
    seq_start = time.perf_counter()
    seq_count = 0
    for query in QUERIES:
        for _ in range(3):  # 3 runs each
            start = time.perf_counter()
            search.search(query, top_k=5)
            lat = (time.perf_counter() - start) * 1000
            latencies.append(lat)
            seq_count += 1
    seq_duration = time.time() - seq_start
    seq_throughput = seq_count / seq_duration
    seq_latency = statistics.mean(latencies[-seq_count:])
    print(f"  Sequential: {seq_count} queries in {seq_duration:.2f}s")
    print(f"  Throughput: {seq_throughput:.1f} queries/sec")
    print(f"  Avg latency: {seq_latency:.1f}ms")
    print()
    
    # Concurrent load test
    print(f"--- Concurrent Load Test ({concurrency} threads, {duration}s each) ---")
    
    threads = []
    query_idx = 0
    
    load_start = time.time()
    
    for t in range(concurrency):
        query = QUERIES[query_idx % len(QUERIES)]
        query_idx += 1
        thread = threading.Thread(
            target=query_worker,
            args=(search, query, t, duration)
        )
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    load_duration = time.time() - load_start
    
    print()
    print("=" * 60)
    print("LOAD BENCHMARK RESULTS")
    print("=" * 60)
    print()
    
    if latencies:
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        
        p50 = sorted_lat[int(n * 0.50)]
        p95 = sorted_lat[int(n * 0.95)]
        p99 = sorted_lat[int(n * 0.99)]
        
        mean = statistics.mean(latencies)
        median = statistics.median(latencies)
        
        actual_throughput = throughput_count / load_duration if load_duration > 0 else 0
        
        print(f"Total queries:     {throughput_count}")
        f"Duration:          {load_duration:.2f}s"
        print(f"Actual throughput: {actual_throughput:.1f} queries/sec")
        print()
        print(f"Latency (all {len(latencies)} samples):")
        print(f"  Mean:           {mean:.1f}ms")
        print(f"  Median:         {median:.1f}ms")
        print(f"  P50:            {p50:.1f}ms")
        print(f"  P95:            {p95:.1f}ms")
        print(f"  P99:            {p99:.1f}ms")
        print(f"  Min:            {min(latencies):.1f}ms")
        print(f"  Max:            {max(latencies):.1f}ms")
        print()
        
        if errors:
            print(f"Errors: {len(errors)}")
            for err in errors[:5]:
                print(f"  - {err}")
            print()
    
    # Comparison
    print("=" * 60)
    print("PERFORMANCE ASSESSMENT")
    print("=" * 60)
    
    if not errors and mean < 500:
        rating = "🟢 Excellent"
        comment = "No errors, mean latency < 500ms"
    elif not errors and mean < 1000:
        rating = "🟡 Good"
        comment = "No errors, mean latency < 1s"
    elif errors:
        rating = "🟠 Fair"
        comment = f"Some errors occurred ({len(errors)})"
    else:
        rating = "🔴 Slow"
        comment = "High latency or many errors"
    
    print(f"Rating: {rating}")
    print(f"Comment: {comment}")
    
    print()
    
    return {
        'throughput': actual_throughput,
        'mean_latency': mean,
        'p99_latency': p99,
        'errors': len(errors),
        'rating': rating,
    }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OCM-Sup Load Benchmark")
    parser.add_argument('--concurrency', type=int, default=5, help='Number of concurrent threads')
    parser.add_argument('--duration', type=int, default=10, help='Duration per thread in seconds')
    args = parser.parse_args()
    
    results = run_load_test(concurrency=args.concurrency, duration=args.duration)
    
    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
