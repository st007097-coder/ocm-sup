#!/usr/bin/env python3
"""
Graph Search Channel for OCM Sup
Uses wiki entities and their relationships for graph-based search
"""

import os
import re
import yaml
import numpy as np
import networkx as nx
import community as community_louvain
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


@dataclass
class DocSource:
    """Represents a document with its source files for overlap calculation"""
    path: str
    title: str
    doc_type: str  # 'entity', 'concept', 'source', etc.
    sources: List[str]  # List of source file paths (from frontmatter sources:[])
    entity_id: str  # The entity ID this doc represents (if any)


class GraphSearchChannel:
    """
    Graph-based search using wiki entities and relationships
    
    Implements 4-Signal Relevance Model:
    1. Direct link (×3.0) - entity relationships via [[wikilinks]]
    2. Source overlap (×4.0) - pages sharing same raw source
    3. Adamic-Adar (×1.5) - shared common neighbors
    4. Type affinity (×1.0) - same page type bonus
    """
    
    def __init__(self, wiki_path: str = "/root/.openclaw/workspace/wiki"):
        self.wiki_path = Path(wiki_path)
        
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.entity_name_to_id: Dict[str, str] = {}  # lowercase name -> node id
        
        # Source overlap support
        self.all_docs: Dict[str, DocSource] = {}  # path -> DocSource for ALL docs
        self.source_to_docs: Dict[str, Set[str]] = {}  # source_path -> set of doc paths
        
        # Adamic-Adar: neighbor sets for each node
        self.node_neighbors: Dict[str, Set[str]] = {}  # node_id -> set of neighbor node_ids
        
        # P3.A: Path to entity mapping (for community context lookup)
        self.path_to_entity_id: Dict[str, str] = {}  # path -> entity_id
        
        self._load_entities()
        self._load_all_docs_for_source_overlap()
        self._build_graph()
        self._build_neighbor_sets()
        self._detect_communities_louvain()  # P3: Louvain Community Detection
    
    def _extract_frontmatter(self, content: str) -> Optional[Dict]:
        """Extract YAML frontmatter from markdown"""
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            try:
                return yaml.safe_load(match.group(1))
            except:
                return None
        return None
    
    def _load_all_docs_for_source_overlap(self):
        """Load ALL wiki documents (not just entities) to support source overlap signal.
        
        We need this because source overlap requires knowing which documents
        share the same raw source files (from frontmatter sources:[]).
        """
        docs_loaded = 0
        
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
                    
                    rel_path = str(filepath.relative_to(self.wiki_path))
                    title = fm.get('title', filepath.stem)
                    doc_type = fm.get('type', fm.get('pageType', 'unknown'))
                    sources = fm.get('sources', [])
                    
                    # Map entity_id for this doc (may be an entity or just a doc that references entities)
                    entity_id = fm.get('id', '') or fm.get('title', '') or ''
                    
                    doc_source = DocSource(
                        path=rel_path,
                        title=str(title),
                        doc_type=str(doc_type),
                        sources=[str(s) for s in sources] if sources else [],
                        entity_id=str(entity_id)
                    )
                    self.all_docs[rel_path] = doc_source
                    
                    # Build source -> docs reverse index
                    for source in doc_source.sources:
                        if source not in self.source_to_docs:
                            self.source_to_docs[source] = set()
                        self.source_to_docs[source].add(rel_path)
                    
                    docs_loaded += 1
                    
                except Exception as e:
                    pass
        
        # print(f"Loaded {docs_loaded} docs for source overlap analysis")
        # print(f"  Source references: {len(self.source_to_docs)} unique sources")
    
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
                    
                    # P3.A: Map path -> entity_id
                    self.path_to_entity_id[node.path] = node.id
                    
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
        
        # print(f"Loaded {entities_loaded} entities")
        # for node in self.nodes.values():
        #     print(f"  - {node.name} ({node.id}): {len(node.relationships)} relationships")
    
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
        
        # print(f"Built graph with {len(self.edges)} edges")
    
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
    
    def _build_neighbor_sets(self):
        """Build neighbor sets for Adamic-Adar calculation."""
        for node in self.nodes.values():
            neighbors = set()
            for edge in self.edges:
                if edge.source_id == node.id:
                    neighbors.add(edge.target_id)
                elif edge.target_id == node.id:
                    neighbors.add(edge.source_id)
            self.node_neighbors[node.id] = neighbors
        
        # print(f"Built neighbor sets for {len(self.node_neighbors)} nodes")
    
    def _detect_communities_louvain(self):
        """Detect communities using Louvain algorithm.
        
        P3: Louvain Community Detection (2026-04-22)
        - Runs once during initialization
        - Caches community assignments for each entity
        - Uses modularity optimization
        """
        if len(self.edges) == 0:
            # print("Louvain: No edges, skipping community detection")
            self.entity_to_community: Dict[str, int] = {}
            self.communities: Dict[int, Set[str]] = {}
            return
        
        # Build networkx graph from edges
        G = nx.Graph()
        for node in self.nodes.values():
            G.add_node(node.id)
        for edge in self.edges:
            G.add_edge(edge.source_id, edge.target_id)
        
        # Run Louvain community detection
        partition = community_louvain.best_partition(G, randomize=False)
        
        # Store entity -> community mapping
        self.entity_to_community: Dict[str, int] = partition
        
        # Build communities -> members mapping
        self.communities: Dict[int, Set[str]] = defaultdict(set)
        for entity_id, community_id in partition.items():
            self.communities[community_id].add(entity_id)
        
        # print(f"Louvain: Detected {len(self.communities)} communities from {len(partition)} entities")
        
        # Show top communities by size
        community_sizes = sorted([(cid, len(members)) for cid, members in self.communities.items()], 
                                  key=lambda x: x[1], reverse=True)
        # print(f"  Top 5 communities by size: {community_sizes[:5]}")
    
    def get_entity_community(self, entity_id: str) -> Optional[int]:
        """Get community ID for an entity."""
        return self.entity_to_community.get(entity_id)
    
    def get_community_members(self, community_id: int) -> List[str]:
        """Get all entity IDs in a community."""
        return list(self.communities.get(community_id, []))
    
    def get_related_in_community(self, entity_id: str) -> List[Dict]:
        """Get other entities in the same community as the given entity."""
        community_id = self.entity_to_community.get(entity_id)
        if community_id is None:
            return []
        
        members = self.communities.get(community_id, set()) - {entity_id}
        related = []
        for mid in members:
            node = self.nodes.get(mid)
            if node:
                related.append({
                    'id': node.id,
                    'name': node.name,
                    'type': node.entity_type
                })
        return related
    
    def _calculate_source_overlap(self, query_doc_path: str, candidate_path: str) -> float:
        """Calculate source overlap score between two documents.
        
        Signal: Source overlap (×4.0)
        If two pages share the same raw source file, they are related.
        """
        if query_doc_path not in self.all_docs or candidate_path not in self.all_docs:
            return 0.0
        
        query_sources = set(self.all_docs[query_doc_path].sources)
        candidate_sources = set(self.all_docs[candidate_path].sources)
        
        if not query_sources or not candidate_sources:
            return 0.0
        
        # Count shared sources
        shared = query_sources & candidate_sources
        
        if not shared:
            return 0.0
        
        # Score: more shared sources = higher score
        # Using log scaling to prevent one doc dominating
        return min(len(shared) / 2.0, 2.0)  # Max 2.0 for having 2+ shared sources
    
    def _calculate_adamic_adar(self, query_node_id: str, candidate_node_id: str) -> float:
        """Calculate Adamic-Adar score between two nodes.
        
        Signal: Adamic-Adar (×1.5)
        Pages that share common neighbors get higher scores.
        Weighted by neighbor degree (rare connections = more signal).
        """
        if query_node_id not in self.node_neighbors or candidate_node_id not in self.node_neighbors:
            return 0.0
        
        query_neighbors = self.node_neighbors[query_node_id]
        candidate_neighbors = self.node_neighbors[candidate_node_id]
        
        if not query_neighbors or not candidate_neighbors:
            return 0.0
        
        # Find common neighbors (excluding the two nodes themselves)
        common = query_neighbors & candidate_neighbors
        common = common - {query_node_id, candidate_node_id}
        
        if not common:
            return 0.0
        
        # Adamic-Adar: sum of 1/log(degree) for each common neighbor
        score = 0.0
        for neighbor in common:
            degree = len(self.node_neighbors.get(neighbor, set()))
            if degree > 1:
                score += 1.0 / (np.log(degree) + 0.1)  # +0.1 to avoid log(0)
        
        return min(score, 3.0)  # Cap at 3.0 to prevent overflow
    
    def _calculate_type_affinity(self, query_node_id: str, candidate_node_id: str) -> float:
        """Calculate type affinity score.
        
        Signal: Type affinity (×1.0)
        Bonus for same page type (entity↔entity, concept↔concept).
        """
        if query_node_id not in self.nodes or candidate_node_id not in self.nodes:
            return 0.0
        
        query_type = self.nodes[query_node_id].entity_type
        candidate_type = self.nodes[candidate_node_id].entity_type
        
        if query_type == candidate_type:
            return 1.0
        
        return 0.0
    
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
        Search documents by traversing entity relationships.
        
        Implements 4-Signal Relevance Model scoring:
        1. Direct link (×3.0) - from BFS path length
        2. Source overlap (×4.0) - shared sources
        3. Adamic-Adar (×1.5) - shared neighbors
        4. Type affinity (×1.0) - same type bonus
        
        Args:
            query: Search query (may contain entity names)
            max_depth: Maximum BFS traversal depth
        
        Returns:
            List of result dicts with 4-signal scores
        """
        # Find matching entities
        matching_entity_ids = self._find_matching_entities(query)
        
        if not matching_entity_ids:
            return []
        
        # Get query node info for scoring signals
        query_node = self.nodes.get(matching_entity_ids[0])
        query_doc_path = query_node.path if query_node else None
        query_type = query_node.entity_type if query_node else None
        
        # Traverse graph from matching entities
        traversed = self._bfs_traverse(matching_entity_ids, max_depth=max_depth)
        
        # Build results with 4-signal scoring
        results = []
        for node_id, base_score, path in traversed:
            node = self.nodes.get(node_id)
            if not node:
                continue
            
            # Calculate 4 signals
            # Signal 1: Direct link (×3.0) - already encoded in base_score from BFS
            direct_link_score = base_score * 3.0
            
            # Signal 2: Source overlap (×4.0)
            source_overlap = self._calculate_source_overlap(query_doc_path, node.path)
            source_overlap_score = source_overlap * 4.0
            
            # Signal 3: Adamic-Adar (×1.5)
            adamic_adar = self._calculate_adamic_adar(matching_entity_ids[0], node_id)
            adamic_adar_score = adamic_adar * 1.5
            
            # Signal 4: Type affinity (×1.0)
            type_affinity = self._calculate_type_affinity(matching_entity_ids[0], node_id)
            type_affinity_score = type_affinity * 1.0
            
            # Combined score
            total_score = direct_link_score + source_overlap_score + adamic_adar_score + type_affinity_score
            
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
                'score': total_score,
                'base_score': base_score,
                'direct_link': direct_link_score,
                'source_overlap': source_overlap_score,
                'adamic_adar': adamic_adar_score,
                'type_affinity': type_affinity_score,
                'path_nodes': [self.nodes.get(nid, type('N', (), {'name': nid})()).name for nid in path],
                'edge_info': edge_text,
                'source': 'graph'
            })
        
        # Sort by total score
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
    
    wiki_path = "/root/.openclaw/workspace/wiki"
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