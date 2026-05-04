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
sys.path.insert(0, '/home/jacky/.openclaw/workspace/skills/triple-stream-search/scripts')

from flask import Flask, request, jsonify
from triple_stream_search import TripleStreamSearch

app = Flask(__name__)

# Global search instance
search = None
stats = {
    'total_requests': 0,
    'queries': {},
    'last_query': None,
    'last_query_time': None,
}

def init_search():
    """Initialize Triple-Stream Search"""
    global search
    wiki_path = '/home/jacky/.openclaw/workspace/wiki'
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
    return jsonify(stats)

@app.route('/search')
def search_get():
    """GET search endpoint
    
    Query params:
        q: Search query (required)
        top_k: Number of results (default: 5, max: 20)
    """
    global stats
    
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'Missing query parameter: q'}), 400
    
    try:
        top_k = min(int(request.args.get('top_k', 5)), 20)
    except ValueError:
        top_k = 5
    
    # Perform search
    results = search.search(query, top_k=top_k)
    
    # Update stats
    stats['total_requests'] += 1
    stats['queries'][query] = stats['queries'].get(query, 0) + 1
    stats['last_query'] = query
    stats['last_query_time'] = datetime.now().isoformat()
    
    # Format results
    formatted_results = []
    for r in results:
        formatted_results.append({
            'title': r['title'],
            'path': r['path'],
            'rrf_score': round(r['rrf_score'], 4),
            'sources': r['sources'],
            'bm25_score': round(r['bm25_score'], 2),
            'vector_score': round(r.get('vector_score', 0), 3),
            'graph_score': round(r.get('graph_score', 0), 3),
        })
    
    return jsonify({
        'query': query,
        'top_k': top_k,
        'result_count': len(formatted_results),
        'results': formatted_results,
        'timestamp': datetime.now().isoformat(),
    })

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
    
    # Format results
    formatted_results = []
    for r in results:
        formatted_results.append({
            'title': r['title'],
            'path': r['path'],
            'rrf_score': round(r['rrf_score'], 4),
            'sources': r['sources'],
            'bm25_score': round(r['bm25_score'], 2),
            'vector_score': round(r.get('vector_score', 0), 3),
            'graph_score': round(r.get('graph_score', 0), 3),
        })
    
    return jsonify({
        'query': query,
        'top_k': top_k,
        'result_count': len(formatted_results),
        'results': formatted_results,
        'timestamp': datetime.now().isoformat(),
    })

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