#!/usr/bin/env python3
"""
Graph Search Channel for OCM Sup
Uses wiki entities and their relationships for graph-based search
"""

import os
import re
import yaml
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict, Set, Optional
from dataclasses import dataclass


@dataclass
class GraphNode:
    """Represents an entity node in the graph"""
    id: str
    name: str
    entity_type: str
    path: str
    relationships: List[Dict]
    content_snippet: str = ""

@dataclass  
class GraphEdge:
    """Represents a relationship between entities"""
    source_id: str
    target_id: str
    relationship_type: str
    text: str = ""


class GraphSearchChannel:
    """
    Graph-based search using wiki entities and relationships
    
    Architecture:
    - Load wiki entities with their relationships
    - Build graph structure (nodes + edges)
    - When query matches entity name, traverse relationships
    - Return related entities and their source documents
    """
    
    def __init__(self, wiki_path: str = "/home/jacky/.openclaw/workspace/wiki"):
        self.wiki_path = Path(wiki_path)
        
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.entity_name_to_id: Dict[str, str] = {}  # lowercase name -> node id
        
        self._load_entities()
        self._build_graph()
    
    def _extract_frontmatter(self, content: str) -> Optional[Dict]:
        """Extract YAML frontmatter from markdown"""
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            try:
                return yaml.safe_load(match.group(1))
            except:
                return None
        return None
    
    def _is_entity_file(self, filepath: Path) -> bool:
        """Check if a file represents an entity"""
        # Entities are typically in entities/ folder or have type: entity in frontmatter
        if 'entities' in str(filepath):
            return True
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            fm = self._extract_frontmatter(content)
            if fm and fm.get('type') == 'entity':
                return True
        except:
            pass
        
        return False
    
    def _load_entities(self):
        """Load all entities from wiki"""
        entities_loaded = 0
        
        for root, dirs, files in os.walk(self.wiki_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if not file.endswith(('.md', '.markdown')):
                    continue
                
                filepath = Path(root) / file
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    fm = self._extract_frontmatter(content)
                    if not fm:
                        continue
                    
                    # Check if this is an entity
                    file_type = fm.get('type', '')
                    is_entity = ('entities' in str(filepath)) or (file_type == 'entity')
                    
                    if not is_entity:
                        continue
                    
                    # Extract entity info
                    entity_id = fm.get('id', '') or fm.get('title', '') or filepath.stem
                    entity_name = fm.get('title', filepath.stem)
                    entity_type = fm.get('entity_type', fm.get('type', 'unknown'))
                    relationships = fm.get('relationships', [])
                    
                    # Create node
                    node = GraphNode(
                        id=str(entity_id),
                        name=str(entity_name),
                        entity_type=str(entity_type),
                        path=str(filepath.relative_to(self.wiki_path)),
                        relationships=list(relationships) if relationships else [],
                        content_snippet=content[:500]
                    )
                    
                    self.nodes[node.id] = node
                    
                    # Index by lowercase name for search
                    self.entity_name_to_id[node.name.lower()] = node.id
                    self.entity_name_to_id[node.name] = node.id
                    
                    # Also index individual words
                    for word in node.name.lower().split():
                        if len(word) >= 2:
                            self.entity_name_to_id[word] = node.id
                    
                    entities_loaded += 1
                    
                except Exception as e:
                    pass
        
        print(f"Loaded {entities_loaded} entities")
        for node in self.nodes.values():
            print(f"  - {node.name} ({node.id}): {len(node.relationships)} relationships")
    
    def _build_graph(self):
        """Build edges from entity relationships"""
        for node in self.nodes.values():
            for rel in node.relationships:
                target = rel.get('target', '')
                rel_type = rel.get('type', 'related')
                text = rel.get('text', '')
                
                # Find target node
                target_id = None
                if target in self.nodes:
                    target_id = target
                elif target.lower() in self.entity_name_to_id:
                    target_id = self.entity_name_to_id[target.lower()]
                
                if target_id:
                    edge = GraphEdge(
                        source_id=node.id,
                        target_id=target_id,
                        relationship_type=rel_type,
                        text=text
                    )
                    self.edges.append(edge)
        
        print(f"Built graph with {len(self.edges)} edges")
    
    def _find_matching_entities(self, query: str) -> List[str]:
        """Find entity IDs that match the query"""
        query_lower = query.lower()
        query_words = query_lower.split()
        
        matching_ids = set()
        
        # Exact match first
        if query in self.entity_name_to_id:
            matching_ids.add(self.entity_name_to_id[query])
        if query_lower in self.entity_name_to_id:
            matching_ids.add(self.entity_name_to_id[query_lower])
        
        # Word-by-word match
        for word in query_words:
            if len(word) >= 2:
                if word in self.entity_name_to_id:
                    matching_ids.add(self.entity_name_to_id[word])
        
        # Partial match in entity names
        for name, node_id in self.entity_name_to_id.items():
            if query_lower in name or name in query_lower:
                if len(name) >= 2:
                    matching_ids.add(node_id)
        
        return list(matching_ids)
    
    def _bfs_traverse(
        self, 
        start_ids: List[str], 
        max_depth: int = 2,
        max_results: int = 20
    ) -> List[Tuple[str, float, List[str]]]:
        """
        BFS traversal from start entities
        
        Returns:
            List of (node_id, score, path) tuples
        """
        visited = set(start_ids)
        queue = [(node_id, 0, [node_id]) for node_id in start_ids]
        results = []
        
        while queue and len(results) < max_results:
            current_id, depth, path = queue.pop(0)
            
            if depth > 0:  # Don't include start node in results
                # Score based on path length (shorter = higher score)
                score = 1.0 / (depth + 1)
                results.append((current_id, score, path))
            
            if depth >= max_depth:
                continue
            
            # Find neighbors
            for edge in self.edges:
                if edge.source_id == current_id and edge.target_id not in visited:
                    visited.add(edge.target_id)
                    new_path = path + [edge.target_id]
                    queue.append((edge.target_id, depth + 1, new_path))
                
                elif edge.target_id == current_id and edge.source_id not in visited:
                    visited.add(edge.source_id)
                    new_path = path + [edge.source_id]
                    queue.append((edge.source_id, depth + 1, new_path))
        
        return results
    
    def search_by_entities(self, query: str, max_depth: int = 2) -> List[Dict]:
        """
        Search documents by traversing entity relationships
        
        Args:
            query: Search query (may contain entity names)
            max_depth: Maximum BFS traversal depth
        
        Returns:
            List of result dicts with entity info and paths
        """
        # Find matching entities
        matching_entity_ids = self._find_matching_entities(query)
        
        if not matching_entity_ids:
            return []
        
        # Traverse graph from matching entities
        traversed = self._bfs_traverse(matching_entity_ids, max_depth=max_depth)
        
        # Build results
        results = []
        for node_id, score, path in traversed:
            node = self.nodes.get(node_id)
            if node:
                # Find the edge that led to this result
                edge_text = ""
                if len(path) >= 2:
                    prev_id = path[-2]
                    for edge in self.edges:
                        if edge.source_id == prev_id and edge.target_id == node_id:
                            edge_text = f" --{edge.relationship_type}--> "
                            break
                        elif edge.target_id == prev_id and edge.source_id == node_id:
                            edge_text = f" <--{edge.relationship_type}-- "
                            break
                
                results.append({
                    'title': node.name,
                    'path': node.path,
                    'entity_type': node.entity_type,
                    'score': score,
                    'path_nodes': [self.nodes.get(nid, type('N', (), {'name': nid})()).name for nid in path],
                    'edge_info': edge_text,
                    'source': 'graph'
                })
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:20]
    
    def get_entity_info(self, entity_name: str) -> Optional[Dict]:
        """Get detailed info about a specific entity"""
        entity_id = self.entity_name_to_id.get(entity_name.lower())
        if not entity_id:
            return None
        
        node = self.nodes.get(entity_id)
        if not node:
            return None
        
        # Get related entities
        related = []
        for edge in self.edges:
            if edge.source_id == entity_id:
                target_node = self.nodes.get(edge.target_id)
                if target_node:
                    related.append({
                        'name': target_node.name,
                        'type': edge.relationship_type,
                        'direction': 'outgoing'
                    })
            elif edge.target_id == entity_id:
                source_node = self.nodes.get(edge.source_id)
                if source_node:
                    related.append({
                        'name': source_node.name,
                        'type': edge.relationship_type,
                        'direction': 'incoming'
                    })
        
        return {
            'id': node.id,
            'name': node.name,
            'type': node.entity_type,
            'path': node.path,
            'relationships': related,
            'content_snippet': node.content_snippet[:300]
        }
    
    def get_stats(self) -> Dict:
        """Get graph statistics"""
        return {
            'entity_count': len(self.nodes),
            'edge_count': len(self.edges),
            'indexed_names': len(self.entity_name_to_id),
        }


def test_graph_search():
    """Test the graph search channel"""
    print("🧪 Testing Graph Search Channel")
    print("=" * 50)
    
    wiki_path = "/home/jacky/.openclaw/workspace/wiki"
    graph = GraphSearchChannel(wiki_path=wiki_path)
    
    stats = graph.get_stats()
    print(f"\n📊 Graph Stats:")
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    # Test queries
    test_queries = [
        "阿星",
        "期哥",
        "古洞站",
        "OCM Sup",
    ]
    
    print(f"\n🔍 Test Graph Searches:")
    for query in test_queries:
        print(f"\n   Query: {query}")
        
        # Show entity info
        entity_info = graph.get_entity_info(query)
        if entity_info:
            print(f"   📦 Entity: {entity_info['name']} ({entity_info['type']})")
            print(f"   📄 Path: {entity_info['path']}")
            if entity_info['relationships']:
                print(f"   🔗 Related ({len(entity_info['relationships'])}):")
                for rel in entity_info['relationships'][:3]:
                    print(f"      - {rel['name']} ({rel['type']}) [{rel['direction']}]")
        
        # Graph search
        results = graph.search_by_entities(query)
        print(f"   📊 Graph search found {len(results)} related docs")
        for r in results[:3]:
            print(f"      - {r['title']} (score={r['score']:.2f})")
            print(f"        path: {' -> '.join(r['path_nodes'])}")
    
    print("\n✅ Graph Search test complete")


if __name__ == "__main__":
    test_graph_search()