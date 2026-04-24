#!/usr/bin/env python3
"""Silent benchmark - suppresses all output during init"""
import sys
import os

# Suppress everything during import
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

sys.path.insert(0, '/root/.openclaw/workspace/OCM-Sup/scripts')
from triple_stream_search import TripleStreamSearch

search = TripleStreamSearch(wiki_path='/root/.openclaw/workspace/wiki')

# Restore output for benchmark results
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

queries = [
    ('hermes', 'Hermes'),
    ('古洞站', 'Kwu Tung'),
    ('期哥', '期哥'),
    ('OpenClaw', 'OpenClaw'),
    ('阿星', '阿星'),
    ('即夢', '即夢'),
    ('EvoMap', 'EvoMap'),
    ('OCM Sup', 'OCM Sup'),
    ('BM25', 'BM25'),
    ('Triple-Stream', 'Triple-Stream'),
    ('RRF', 'RRF'),
    ('Query Expansion', 'Query Expansion'),
    ('Retention Scan', 'Retention Scan'),
    ('Tavily', 'Tavily'),
    ('Quantity Surveyor', 'Quantity Surveyor'),
]

results = []
for query, expected in queries:
    r = search.search(query, top_k=5)
    top1 = r[0]['title'] if r else 'NONE'
    top1_path = r[0]['path'] if r else ''
    
    keywords = expected.lower().split()
    hit = any(kw in top1.lower() or kw in top1_path.lower() for kw in keywords)
    hit_symbol = '✓' if hit else '?'
    
    print(f"{hit_symbol} {query:<20} -> {top1[:45]}")
    results.append((query, top1, hit))

print("="*80)
hits = sum(1 for _, _, h in results if h)
print(f"Hit Rate: {hits}/{len(results)} = {hits/len(results)*100:.1f}%")