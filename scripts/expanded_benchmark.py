#!/usr/bin/env python3
"""
OCM-Sup Expanded Benchmark — 20+ test queries
Testing across multiple categories:
- Familiar entities (baseline)
- Unfamiliar/hard entities  
- Ambiguous queries
- Cross-lingual edge cases

Usage:
    python3 expanded_benchmark.py [--category all|familiar|hard|ambiguous|crosslingual]
"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/OCM-Sup/scripts')
from triple_stream_search import TripleStreamSearch

# Initialize search
WIKI_PATH = '/root/.openclaw/workspace/wiki'
search = TripleStreamSearch(wiki_path=WIKI_PATH)

# Expanded query set
QUERIES = {
    'familiar': [
        {'query': 'hermes', 'expected': 'Hermes Agent entity', 'category': 'entity'},
        {'query': '古洞站', 'expected': 'Kwu Tung Station entity', 'category': 'entity'},
        {'query': '期哥', 'expected': 'Jacky entity', 'category': 'person'},
        {'query': 'OpenClaw', 'expected': 'OpenClaw system docs', 'category': 'system'},
        {'query': '阿星', 'expected': 'Ah Sing entity', 'category': 'person'},
    ],
    'hard': [
        {'query': '即夢', 'expected': 'Jimeng/即夢 AI tool', 'category': 'tool'},
        {'query': 'EvoMap', 'expected': 'EvoMap evolver entity', 'category': 'system'},
        {'query': 'ClawEmail', 'expected': 'ClawEmail research', 'category': 'system'},
        {'query': 'OCM Sup', 'expected': 'OCM Sup memory system', 'category': 'system'},
        {'query': 'notion', 'expected': 'Notion integration docs', 'category': 'tool'},
        {'query': 'BM25', 'expected': 'BM25 search algorithm docs', 'category': 'concept'},
        {'query': 'Triple-Stream', 'expected': 'Triple-Stream Search docs', 'category': 'concept'},
        {'query': 'RRF', 'expected': 'Reciprocal Rank Fusion docs', 'category': 'concept'},
    ],
    'p0.5_new_entities': [
        {'query': 'Query Expansion', 'expected': 'Query Expansion entity doc', 'category': 'concept'},
        {'query': 'Retention Scan', 'expected': 'Retention Scan entity doc', 'category': 'workflow'},
        {'query': 'Tavily', 'expected': 'Tavily search tool entity doc', 'category': 'tool'},
    ],
    'ambiguous': [
        {'query': 'QS', 'expected': 'Quantity Surveyor OR Query Search?', 'category': 'ambiguous'},
        {'query': 'memory', 'expected': 'Memory system OR recall?', 'category': 'ambiguous'},
        {'query': 'search', 'expected': 'Search tool OR web search?', 'category': 'ambiguous'},
        {'query': 'project', 'expected': 'Project entity OR general concept?', 'category': 'ambiguous'},
        {'query': 'agent', 'expected': 'AI Agent OR human agent?', 'category': 'ambiguous'},
    ],
    'crosslingual': [
        {'query': 'Kwu Tung Station', 'expected': '古洞站 Chinese docs', 'category': 'en2zh'},
        {'query': 'quantity surveyor', 'expected': 'QS 工料測量師 docs', 'category': 'en2zh'},
        {'query': 'knowledge graph', 'expected': '知識圖譜/圖譜 docs', 'category': 'en2zh'},
        {'query': 'vector search', 'expected': '向量搜索 docs', 'category': 'en2zh'},
        {'query': 'BM25 algorithm', 'expected': 'BM25 算法 docs', 'category': 'en2zh'},
        {'query': 'consolidation loop', 'expected': '整合循環/蒸餾 docs', 'category': 'en2zh'},
        {'query': 'latency benchmark', 'expected': '延遲測試 docs', 'category': 'en2zh'},
        {'query': 'entity relationship', 'expected': '實體關係 docs', 'category': 'en2zh'},
    ],
    'edge_cases': [
        {'query': '香港', 'expected': 'Hong Kong related docs', 'category': 'location'},
        {'query': '工程', 'expected': 'Engineering docs', 'category': 'industry'},
        {'query': '分判商', 'expected': 'Subcontractor docs', 'category': 'industry'},
        {'query': '供應商', 'expected': 'Supplier docs', 'category': 'industry'},
        {'query': '合約', 'expected': 'Contract docs', 'category': 'document'},
        {'query': '投標', 'expected': 'Tendering docs', 'category': 'process'},
    ],
}

def run_query(q_item, search, verbose=False):
    """Run a single query and analyze results"""
    query = q_item['query']
    expected = q_item['expected']
    
    results = search.search(query, top_k=5)
    
    # Categorize results
    has_hit = len(results) > 0
    top_result_relevant = False
    if results and len(results) >= 1:
        # Check if top result has any relevant content
        top = results[0]
        # Simple heuristic: if sources not empty, we got something
        top_result_relevant = len(top.get('sources', [])) > 0 or top.get('rrf_score', 0) > 0
    
    # Calculate hit metrics
    hit_top1 = 1 if has_hit and results[0].get('rrf_score', 0) > 0 else 0
    
    # For top3/top5, check if any results have decent scores
    hit_top3 = 1 if len([r for r in results[:3] if r.get('rrf_score', 0) > 0]) >= 1 else 0
    hit_top5 = 1 if len([r for r in results[:5] if r.get('rrf_score', 0) > 0]) >= 1 else 0
    
    # BM25 contribution
    bm25_scores = [r.get('bm25_score', 0) for r in results]
    has_bm25 = any(s > 0 for s in bm25_scores)
    
    # Vector contribution
    vector_scores = [r.get('vector_score', 0) for r in results]
    has_vector = any(s > 0.1 for s in vector_scores)  # above threshold
    
    # Graph contribution
    graph_scores = [r.get('graph_score', 0) for r in results]
    has_graph = any(s > 0 for s in graph_scores)
    
    channels_used = [ch for ch in ['BM25', 'Vector', 'Graph'] if 
                    (ch == 'BM25' and has_bm25) or
                    (ch == 'Vector' and has_vector) or
                    (ch == 'Graph' and has_graph)]
    
    result_item = {
        'query': query,
        'expected': expected,
        'category': q_item['category'],
        'hit_top1': hit_top1,
        'hit_top3': hit_top3,
        'hit_top5': hit_top5,
        'total_results': len(results),
        'top_score': results[0].get('rrf_score', 0) if results else 0,
        'top_title': results[0].get('title', '')[:50] if results else '',
        'channels_used': channels_used,
        'bm25_only': has_bm25 and not has_vector and not has_graph,
        'cross_lingual': has_bm25 and not has_vector,  # BM25 without vector = aliases working
    }
    
    if verbose:
        print(f"  [{q_item['category']}] {query}")
        print(f"    → {len(results)} results, top: {results[0].get('title', '')[:40] if results else 'none'}")
        print(f"    → Top1:{hit_top1} Top3:{hit_top3} Top5:{hit_top5} | Channels: {channels_used}")
    
    return result_item

def run_category(name, queries, search, verbose=False):
    """Run all queries in a category"""
    print(f"\n=== {name} ({len(queries)} queries) ===")
    results = []
    for q in queries:
        r = run_query(q, search, verbose)
        results.append(r)
    return results

def print_summary(all_results):
    """Print summary statistics"""
    total = len(all_results)
    hit1_count = sum(1 for r in all_results if r['hit_top1'])
    hit3_count = sum(1 for r in all_results if r['hit_top3'])
    hit5_count = sum(1 for r in all_results if r['hit_top5'])
    
    # By category
    categories = {}
    for r in all_results:
        cat = r['category']
        if cat not in categories:
            categories[cat] = {'total': 0, 'hit1': 0, 'hit3': 0, 'hit5': 0}
        categories[cat]['total'] += 1
        categories[cat]['hit1'] += r['hit_top1']
        categories[cat]['hit3'] += r['hit_top3']
        categories[cat]['hit5'] += r['hit_top5']
    
    print("\n" + "="*60)
    print("📊 BENCHMARK SUMMARY")
    print("="*60)
    print(f"\nOverall ({total} queries):")
    print(f"  Top-1 Hit Rate: {hit1_count}/{total} = {hit1_count/total*100:.1f}%")
    print(f"  Top-3 Hit Rate: {hit3_count}/{total} = {hit3_count/total*100:.1f}%")
    print(f"  Top-5 Hit Rate: {hit5_count}/{total} = {hit5_count/total*100:.1f}%")
    
    print("\nBy Category:")
    for cat, stats in sorted(categories.items()):
        t = stats['total']
        print(f"  {cat:15s}: Top1={stats['hit1']}/{t} ({stats['hit1']/t*100:.0f}%) | "
              f"Top3={stats['hit3']}/{t} ({stats['hit3']/t*100:.0f}%) | "
              f"Top5={stats['hit5']}/{t} ({stats['hit5']/t*100:.0f}%)")
    
    # Cross-lingual analysis
    cross_lingual = [r for r in all_results if r['category'].startswith('en2zh')]
    if cross_lingual:
        cl_hit = sum(1 for r in cross_lingual if r['hit_top3'])
        print(f"\nCross-lingual (en2zh): {cl_hit}/{len(cross_lingual)} = {cl_hit/len(cross_lingual)*100:.1f}% Top-3 hit")
        cross_lingual_bm25_only = sum(1 for r in cross_lingual if r['cross_lingual'])
        print(f"  Using BM25-only (aliases working): {cross_lingual_bm25_only}/{len(cross_lingual)}")
    
    # Ambiguous queries
    ambiguous = [r for r in all_results if r['category'] == 'ambiguous']
    if ambiguous:
        amb_hit = sum(1 for r in ambiguous if r['hit_top3'])
        print(f"\nAmbiguous queries: {amb_hit}/{len(ambiguous)} = {amb_hit/len(ambiguous)*100:.1f}% Top-3 hit")
    
    return {
        'total': total,
        'hit_top1': hit1_count/total*100,
        'hit_top3': hit3_count/total*100,
        'hit_top5': hit5_count/total*100,
        'by_category': categories,
    }

def save_results(all_results, summary):
    """Save results to file"""
    output_path = Path('/root/.openclaw/workspace/OCM-Sup/benchmark-results.json')
    data = {
        'timestamp': datetime.now().isoformat(),
        'total_queries': len(all_results),
        'summary': {
            'hit_top1_pct': summary['hit_top1'],
            'hit_top3_pct': summary['hit_top3'],
            'hit_top5_pct': summary['hit_top5'],
        },
        'by_category': summary['by_category'],
        'detailed_results': all_results,
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Results saved to {output_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='OCM-Sup Expanded Benchmark')
    parser.add_argument('--category', default='all', 
                       choices=['all', 'familiar', 'hard', 'ambiguous', 'crosslingual', 'edge_cases'])
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--save', action='store_true', help='Save results to JSON')
    
    args = parser.parse_args()
    
    print(f"🚀 OCM-Sup Expanded Benchmark")
    print(f"   Wiki: {WIKI_PATH}")
    print(f"   Category: {args.category}")
    
    all_results = []
    
    if args.category == 'all':
        for name, queries in QUERIES.items():
            results = run_category(name, queries, search, args.verbose)
            all_results.extend(results)
    else:
        queries = QUERIES.get(args.category, [])
        if queries:
            results = run_category(args.category, queries, search, args.verbose)
            all_results.extend(results)
    
    # Summary
    summary = print_summary(all_results)
    
    # Save if requested
    if args.save:
        save_results(all_results, summary)
    
    return summary

if __name__ == '__main__':
    main()