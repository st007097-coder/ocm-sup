#!/usr/bin/env python3
"""
Triple-Stream Search HTTP API
Provides HTTP endpoints for Triple-Stream Search

Usage:
    python3 search_api.py [--port 5000]

Endpoints:
    GET  /search?q=query&top_k=5  - Search endpoint
    GET  /health                   - Health check
    GET  /stats                    - Search statistics
    POST /search                   - JSON body search
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add Triple-Stream to path
sys.path.insert(0, '/root/.openclaw/workspace/skills/triple-stream-search/scripts')

from flask import Flask, request, jsonify
import time
from triple_stream_search import TripleStreamSearch

app = Flask(__name__)

# Global search instance
search = None
stats = {
    'total_requests': 0,
    'queries': {},
    'last_query': None,
    'last_query_time': None,
    'latencies': [],  # individual request latencies in ms
}

def init_search():
    """Initialize Triple-Stream Search"""
    global search
    wiki_path = '/root/.openclaw/workspace/wiki'
    search = TripleStreamSearch(wiki_path=wiki_path)
    print(f"✅ Triple-Stream Search initialized")
    print(f"   Wiki: {wiki_path}")
    print(f"   Entities: {len(search.graph_channel.nodes)}")

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'entities': len(search.graph_channel.nodes) if search else 0,
    })

@app.route('/stats')
def get_stats():
    """Get search statistics"""
    latencies = stats.get('latencies', [])
    if latencies:
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        p50 = sorted_lat[int(n * 0.50)] if n > 0 else 0
        p95 = sorted_lat[int(n * 0.95)] if n > 0 else 0
        p99 = sorted_lat[int(n * 0.99)] if n > 0 else 0
        latency_stats = {
            'count': n,
            'mean': round(sum(latencies) / n, 2),
            'p50': round(p50, 2),
            'p95': round(p95, 2),
            'p99': round(p99, 2),
            'min': round(min(latencies), 2),
            'max': round(max(latencies), 2),
        }
    else:
        latency_stats = {'count': 0}
    
    return jsonify({
        'total_requests': stats.get('total_requests', 0),
        'unique_queries': len(stats.get('queries', {})),
        'latency_ms': latency_stats,
        'last_query': stats.get('last_query'),
        'last_query_time': stats.get('last_query_time'),
    })

@app.route('/search')
def search_get():
    """GET search endpoint
    
    Query params:
        q: Search query (required)
        top_k: Number of results (default: 5, max: 20)
    """
    global stats
    t0 = time.perf_counter()
    
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'Missing query parameter: q'}), 400
    
    try:
        top_k = min(int(request.args.get('top_k', 5)), 20)
    except ValueError:
        top_k = 5
    
    explain = request.args.get('explain', 'false').lower() == 'true'
    
    # Perform search
    results = search.search(query, top_k=top_k)
    
    # Update stats
    stats['total_requests'] += 1
    stats['queries'][query] = stats['queries'].get(query, 0) + 1
    stats['last_query'] = query
    stats['last_query_time'] = datetime.now().isoformat()
    
    # Get query expansion for explanation
    expansion = search.expander.expand_query(query)
    expanded_query = expansion[0]
    
    # Run all three channels separately for explanation
    bm25_results = search.search_bm25_expanded(query, top_k=top_k * 2)
    vector_results = search.search_vector(query, top_k=top_k * 2)
    graph_results = search.search_graph(query, top_k=top_k * 2)
    
    # Format results
    formatted_results = []
    for r in results:
        result = {
            'title': r['title'],
            'path': r['path'],
            'rrf_score': round(r['rrf_score'], 4),
            'sources': r['sources'],
            'bm25_score': round(r['bm25_score'], 2),
            'vector_score': round(r.get('vector_score', 0), 3),
            'graph_score': round(r.get('graph_score', 0), 3),
        }
        
        if explain:
            # Find doc_idx for this result
            doc_idx = None
            for i, meta in enumerate(search.bm25_metadata):
                if meta['path'] == r['path']:
                    doc_idx = i
                    break
            
            bm25_rank = next((i+1 for i, (di, s) in enumerate(bm25_results) if di == doc_idx), None)
            vector_rank = next((i+1 for i, (di, s) in enumerate(vector_results) if di == doc_idx), None)
            graph_rank = next((i+1 for i, (di, s) in enumerate(graph_results) if di == doc_idx), None)
            
            # Get graph path for this result
            graph_path = None
            for node_id, node in search.graph_channel.nodes.items():
                if node.path == r['path']:
                    path_parts = []
                    for rel in node.relationships[:3]:
                        path_parts.append(f"{node.name} --[{rel['type']}]--> {rel.get('target', '?')}")
                    graph_path = path_parts
                    break
            
            result['explain'] = {
                'bm25_rank': bm25_rank,
                'vector_rank': vector_rank,
                'graph_rank': graph_rank,
                'channels_used': r['sources'],
                'expansion_used': r.get('expansion', []),
            }
            if graph_path:
                result['explain']['graph_path'] = graph_path
        
        formatted_results.append(result)
    
    response = {
        'query': query,
        'expanded_query': expanded_query,
        'top_k': top_k,
        'result_count': len(formatted_results),
        'results': formatted_results,
        'timestamp': datetime.now().isoformat(),
    }
    
    if explain:
        response['channel_stats'] = {
            'bm25_candidates': len(bm25_results),
            'vector_candidates': len(vector_results),
            'graph_candidates': len(graph_results),
            'final_ranked': len(results),
        }
    
    # Record latency
    latency_ms = (time.perf_counter() - t0) * 1000
    stats['latencies'].append(latency_ms)
    if len(stats['latencies']) > 1000:
        stats['latencies'] = stats['latencies'][-1000:]
    return jsonify(response)

@app.route('/search', methods=['POST'])
def search_post():
    """POST search endpoint with JSON body
    
    Body:
    {
        "q": "search query",
        "top_k": 5
    }
    """
    global stats
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400
    
    query = data.get('q', '')
    if not query:
        return jsonify({'error': 'Missing field: q'}), 400
    
    try:
        top_k = min(int(data.get('top_k', 5)), 20)
    except ValueError:
        top_k = 5
    
    # Perform search
    results = search.search(query, top_k=top_k)
    
    # Update stats
    stats['total_requests'] += 1
    stats['queries'][query] = stats['queries'].get(query, 0) + 1
    stats['last_query'] = query
    stats['last_query_time'] = datetime.now().isoformat()
    
    # Get query expansion for explanation
    expansion = search.expander.expand_query(query)
    expanded_query = expansion[0]
    
    # Run all three channels separately for explanation
    bm25_results = search.search_bm25_expanded(query, top_k=top_k * 2)
    vector_results = search.search_vector(query, top_k=top_k * 2)
    graph_results = search.search_graph(query, top_k=top_k * 2)
    
    # Format results
    formatted_results = []
    for r in results:
        result = {
            'title': r['title'],
            'path': r['path'],
            'rrf_score': round(r['rrf_score'], 4),
            'sources': r['sources'],
            'bm25_score': round(r['bm25_score'], 2),
            'vector_score': round(r.get('vector_score', 0), 3),
            'graph_score': round(r.get('graph_score', 0), 3),
        }
        
        if explain:
            # Find doc_idx for this result
            doc_idx = None
            for i, meta in enumerate(search.bm25_metadata):
                if meta['path'] == r['path']:
                    doc_idx = i
                    break
            
            bm25_rank = next((i+1 for i, (di, s) in enumerate(bm25_results) if di == doc_idx), None)
            vector_rank = next((i+1 for i, (di, s) in enumerate(vector_results) if di == doc_idx), None)
            graph_rank = next((i+1 for i, (di, s) in enumerate(graph_results) if di == doc_idx), None)
            
            # Get graph path for this result
            graph_path = None
            for node_id, node in search.graph_channel.nodes.items():
                if node.path == r['path']:
                    path_parts = []
                    for rel in node.relationships[:3]:
                        path_parts.append(f"{node.name} --[{rel['type']}]--> {rel.get('target', '?')}")
                    graph_path = path_parts
                    break
            
            result['explain'] = {
                'bm25_rank': bm25_rank,
                'vector_rank': vector_rank,
                'graph_rank': graph_rank,
                'channels_used': r['sources'],
                'expansion_used': r.get('expansion', []),
            }
            if graph_path:
                result['explain']['graph_path'] = graph_path
        
        formatted_results.append(result)
    
    response = {
        'query': query,
        'expanded_query': expanded_query,
        'top_k': top_k,
        'result_count': len(formatted_results),
        'results': formatted_results,
        'timestamp': datetime.now().isoformat(),
    }
    
    if explain:
        response['channel_stats'] = {
            'bm25_candidates': len(bm25_results),
            'vector_candidates': len(vector_results),
            'graph_candidates': len(graph_results),
            'final_ranked': len(results),
        }
    
    return jsonify(response)

@app.route('/entity/<entity_name>')
def get_entity(entity_name):
    """Get entity by name"""
    entity_name = entity_name.replace('-', ' ')
    
    # Search for the entity
    results = search.search(entity_name, top_k=3)
    
    # Check if entity exists in graph
    entity = search.graph_channel.nodes.get(entity_name.lower())
    if entity:
        return jsonify({
            'name': entity.name,
            'type': entity.entity_type,
            'path': entity.path,
            'relationships': entity.relationships,
        })
    
    return jsonify({'error': 'Entity not found'}), 404

@app.route('/entities')
def list_entities():
    """List all entities"""
    entities = []
    for node_id, node in search.graph_channel.nodes.items():
        entities.append({
            'name': node.name,
            'type': node.entity_type,
            'path': node.path,
        })
    
    return jsonify({
        'count': len(entities),
        'entities': entities,
    })

@app.route('/')
def index():
    """Index page with API documentation"""
    return jsonify({
        'name': 'Triple-Stream Search API',
        'version': '1.0',
        'endpoints': [
            'GET  /search?q=query&top_k=5  - Search (GET)',
            'POST /search                  - Search (POST)',
            'GET  /entity/<name>          - Get entity',
            'GET  /entities               - List entities',
            'GET  /stats                  - Search statistics',
            'GET  /health                 - Health check',
        ],
        'documentation': 'See SKILL.md for full documentation',
    })

def main():
    parser = argparse.ArgumentParser(description='Triple-Stream Search HTTP API')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print("🚀 Starting Triple-Stream Search API...")
    init_search()
    
    print(f"\n📡 API Endpoints:")
    print(f"   GET  http://localhost:{args.port}/search?q=古洞站")
    print(f"   GET  http://localhost:{args.port}/entities")
    print(f"   GET  http://localhost:{args.port}/stats")
    print(f"   GET  http://localhost:{args.port}/health")
    
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()