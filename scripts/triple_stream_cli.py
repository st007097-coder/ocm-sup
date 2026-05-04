#!/usr/bin/env python3
"""
Triple-Stream Search CLI
Usage: python3 triple_stream_cli.py "<query>" [--top-k N]
"""

import sys
import json
import argparse

# Add scripts path
sys.path.insert(0, '/home/jacky/.openclaw/workspace/skills/triple-stream-search/scripts')

from triple_stream_search import TripleStreamSearch

def main():
    parser = argparse.ArgumentParser(description='Triple-Stream Search CLI')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--top-k', type=int, default=5, help='Number of results')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    parser.add_argument('--wiki-path', default='/home/jacky/.openclaw/workspace/wiki', help='Wiki path')
    
    args = parser.parse_args()
    
    # Initialize search
    search = TripleStreamSearch(wiki_path=args.wiki_path)
    
    # Search
    results = search.search(args.query, top_k=args.top_k)
    
    # Output
    if args.format == 'json':
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"🔍 Search: {args.query}")
        print(f"📊 Results: {len(results)}")
        print()
        for i, r in enumerate(results, 1):
            sources = '+'.join(r['sources'])
            print(f"{i}. [{sources}] {r['title']}")
            print(f"   📄 {r['path']}")
            print(f"   📊 RRF={r['rrf_score']:.3f} BM25={r['bm25_score']:.2f} Vec={r['vector_score']:.3f} Graph={r['graph_score']:.2f}")
            print()

if __name__ == '__main__':
    main()