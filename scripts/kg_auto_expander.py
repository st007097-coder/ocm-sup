#!/usr/bin/env python3
"""
KG Auto-Expansion System
Automatically discovers and adds new entities to the Knowledge Graph

OCM Sup 7-Dir 4: Knowledge Graph Auto-Expansion
"""

import os
import re
import json
import hashlib
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime

# For entity extraction
import requests

# Graph structures
from graph_search import GraphSearchChannel, GraphNode, GraphEdge

class KGEntityExtractor:
    """
    Extract entities from documents using patterns and heuristics.
    
    Strategy:
    1. Look for capitalized terms (potential entities)
    2. Look for entity patterns (name, title, role)
    3. Look for relationship indicators
    4. Use embeddings to find similar existing entities
    """
    
    # Patterns for entity detection
    ENTITY_PATTERNS = [
        # Chinese names/terms (2-4 chars)
        r'[\u4e00-\u9fff]{2,4}(?:先生|女士|經理|總監|負責人|顧問|QS|工程師)',
        # English capitalized words
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
        # Quoted terms
        r'"([^"]{2,20})"',
        # Entity-like patterns in markdown
        r'\*\*([^\*]{2,20})\*\*',
        # Projects/Buildings
        r'([A-Z][a-z]+(?:\s+Station|\s+Project|\s+Phase|\s+Line|\s+站))',
    ]
    
    # Relationship indicators
    RELATIONSHIP_PATTERNS = [
        # Chinese
        (r'([\u4e00-\u9fff]{2,4})是([\u4e00-\u9fff]{2,4})的(.+)', 'is'),
        (r'([\u4e00-\u9fff]{2,4})喺([\u4e00-\u9fff]{2,4})做(.+)', 'works_at'),
        (r'([\u4e00-\u9fff]{2,4})隸屬於(.+)', 'belongs_to'),
        # English
        (r'(\w+)\s+(?:works?\s+(?:on|in|at)|is\s+(?:a|an|the)\s+)(\w+)', 'relates_to'),
        (r'(\w+)\s+belongs?\s+to\s+(\w+)', 'belongs_to'),
        (r'(\w+)\s+is\s+(?:a|an)\s+(\w+)', 'is_a'),
    ]
    
    # Known entity types - 擴展版本
    ENTITY_TYPES = {
        'person': {
            'keywords': ['期哥', '阿星', '先生', '女士', '經理', '總監', '負責人', '顧問', 'QS', '工程師', 'Manager', 'Director', 'Engineer', 'Consultant'],
            'patterns': [r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', r'^[\u4e00-\u9fff]{2,4}$'],  # e.g., John Smith, 期哥
        },
        'project': {
            'keywords': ['站', '項目', 'Phase', 'Line', 'Project', '計劃', '工程'],
            'patterns': [r'(?:Station|Project|Line|Phase)[A-Z0-9]', r'[\u4e00-\u9fff]*站'],
        },
        'company': {
            'keywords': ['公司', 'Limited', 'Ltd', 'Inc', 'Corporation', 'Co.', '企業', '供應商', '分判商'],
            'patterns': [r'Limited$', r'Ltd\.?$', r'Inc\.?$', r'Corporation$'],
        },
        'location': {
            'keywords': ['香港', '九龍', '新界', '工地', '地盤', '寫字樓', 'Hong Kong', 'Kowloon'],
            'patterns': [],
        },
        'system': {
            'keywords': ['OCM', 'Sup', 'System', '系統', '引擎', 'Engine', 'Plugin', 'Skill'],
            'patterns': [],
        },
        'technology': {
            'keywords': ['AI', 'LLM', 'API', 'Graph', 'Vector', 'BM25', 'Embedding', 'RAG', 'ChatGPT', 'Claude', 'Ollama'],
            'patterns': [],
        },
    }
    
    def __init__(self, wiki_path: str):
        self.wiki_path = Path(wiki_path)
        self.known_entities: Set[str] = set()
        self.entity_types: Dict[str, str] = {}  # Track entity types (name -> type)
        self.entity_candidates: Dict[str, Dict] = defaultdict(lambda: {
            'name': '',
            'type': 'concept',  # Default to concept
            'sources': [],
            'confidence': 0.0,
            'relationships': [],
        })
    
    def load_known_entities(self, existing_graph: GraphSearchChannel):
        """Load existing entities from the Graph to avoid duplicates"""
        for node_id, node in existing_graph.nodes.items():
            self.known_entities.add(node.name)
            self.known_entities.add(node_id)
            # Also track entity type
            if hasattr(node, 'entity_type'):
                self.entity_types[node.name.lower()] = node.entity_type
                self.entity_types[node_id.lower()] = node.entity_type
    
    def extract_from_document(self, filepath: Path) -> List[Dict]:
        """Extract entities from a single document"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return []
        
        entities_found = []
        doc_hash = hashlib.md5(content[:1000].encode()).hexdigest()
        
        # Check for entities in frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if frontmatter_match:
            fm = frontmatter_match.group(1)
            
            # Extract title
            title_match = re.search(r'^title:\s*(.+?)\s*$', fm, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
                entities_found.append({
                    'name': title,
                    'type': 'document_title',
                    'source': str(filepath),
                    'confidence': 0.9,
                })
            
            # Extract tags
            tags_match = re.search(r'^tags:\s*\[(.*?)\]', fm, re.MULTILINE)
            if tags_match:
                tags = [t.strip() for t in tags_match.group(1).split(',')]
                for tag in tags:
                    if len(tag) >= 2:
                        entities_found.append({
                            'name': tag,
                            'type': 'tag',
                            'source': str(filepath),
                            'confidence': 0.5,
                        })
        
        # Extract using patterns
        for pattern in self.ENTITY_PATTERNS:
            for match in re.finditer(pattern, content):
                text = match.group(1) if match.lastindex else match.group(0)
                text = text.strip()
                
                if len(text) >= 2 and len(text) <= 20:
                    # Check if it's a known entity
                    if text not in self.known_entities:
                        # Determine entity type based on patterns
                        entity_type = self._classify_entity(text)
                        entities_found.append({
                            'name': text,
                            'type': entity_type,
                            'source': str(filepath),
                            'confidence': 0.6,
                        })
        
        # Look for relationships
        relationships = self._extract_relationships(content)
        
        return entities_found, relationships
    
    def _classify_entity(self, text: str) -> str:
        """Classify entity type based on improved type system"""
        for entity_type, type_info in self.ENTITY_TYPES.items():
            # Check keywords
            for keyword in type_info.get('keywords', []):
                if keyword in text:
                    return entity_type
            # Check patterns
            for pattern in type_info.get('patterns', []):
                if re.search(pattern, text):
                    return entity_type
        return 'concept'  # Default to 'concept' instead of 'unknown'
    
    def _extract_relationships(self, content: str) -> List[Tuple[str, str, str]]:
        """Extract relationships from document content"""
        relationships = []
        
        for pattern, rel_type in self.RELATIONSHIP_PATTERNS:
            for match in re.finditer(pattern, content):
                if match.lastindex and match.lastindex >= 2:
                    entity1 = match.group(1).strip()
                    entity2 = match.group(2).strip()
                    if len(entity1) >= 2 and len(entity2) >= 2:
                        relationships.append((entity1, entity2, rel_type))
        
        return relationships
    
    def scan_wiki(self) -> Dict:
        """
        Scan entire wiki and extract all entities and relationships.
        
        Returns:
            {
                'new_entities': [...],
                'new_relationships': [...],
                'stats': {...}
            }
        """
        all_entities = []
        all_relationships = []
        stats = {
            'documents_scanned': 0,
            'entities_found': 0,
            'relationships_found': 0,
            'by_type': defaultdict(int),
        }
        
        markdown_extensions = {'.md', '.markdown'}
        
        for root, dirs, files in os.walk(self.wiki_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if any(file.endswith(ext) for ext in markdown_extensions):
                    filepath = Path(root) / file
                    stats['documents_scanned'] += 1
                    
                    entities, relationships = self.extract_from_document(filepath)
                    all_entities.extend(entities)
                    all_relationships.extend(relationships)
        
        stats['entities_found'] = len(all_entities)
        stats['relationships_found'] = len(all_relationships)
        
        # Deduplicate
        seen_entities = set()
        unique_entities = []
        for e in all_entities:
            key = e['name'].lower()
            if key not in seen_entities:
                seen_entities.add(key)
                unique_entities.append(e)
                stats['by_type'][e['type']] += 1
        
        stats['unique_entities'] = len(unique_entities)
        
        return {
            'new_entities': unique_entities,
            'new_relationships': all_relationships,
            'stats': dict(stats),
        }


class KGAutoExpander:
    """
    Automatically expand the Knowledge Graph with new entities and relationships.
    
    Usage:
        expander = KGAutoExpander(wiki_path="/root/.openclaw/workspace/wiki")
        result = expander.expand()
        print(f"Added {len(result['added_entities'])} new entities")
    """
    
    def __init__(
        self,
        wiki_path: str,
        ollama_url: str = "http://host.docker.internal:11434",
        min_confidence: float = 0.7,
        similarity_threshold: float = 0.92,  # 提高到 0.92，更嚴格
        skip_similarity_check: bool = False,  # 新增：跳過相似性檢查
        dry_run: bool = True,  # 預設 dry-run
    ):
        self.wiki_path = wiki_path
        self.ollama_url = ollama_url
        self.min_confidence = min_confidence
        self.similarity_threshold = similarity_threshold  # 儲存 threshold
        self.skip_similarity_check = skip_similarity_check  # 儲存設定
        self.dry_run = dry_run  # 儲存 dry-run 設定
        
        self.extractor = KGEntityExtractor(wiki_path)
        self.graph = GraphSearchChannel(wiki_path)
        
        # Load known entities to avoid duplicates
        self.extractor.load_known_entities(self.graph)
        
        # Track changes
        self.added_entities: List[Dict] = []
        self.added_relationships: List[Dict] = []
        self.errors: List[str] = []
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using Ollama"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": "nomic-embed-text:latest", "prompt": text[:500]},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('embedding')
        except:
            pass
        return None
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using Levenshtein distance
        Returns value between 0 (completely different) and 1 (identical)
        """
        if s1.lower() == s2.lower():
            return 1.0
        
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        
        distance = self._levenshtein_distance(s1, s2)
        return 1.0 - (distance / max_len)
    
    def _are_entity_types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two entity types are potentially compatible for similarity
        
        Incompatible pairs (probably NOT similar):
        - person vs concept
        - person vs technology
        - project vs technology
        """
        incompatible_pairs = [
            ('person', 'concept'),
            ('person', 'technology'),
            ('project', 'concept'),
            ('project', 'technology'),
            ('location', 'concept'),
            ('location', 'technology'),
        ]
        
        return (type1, type2) not in incompatible_pairs and (type2, type1) not in incompatible_pairs
    
    def _find_similar_entities(self, entity_name: str, threshold: float = None) -> List[str]:
        """Find similar existing entities using multi-stage filtering
        
        Stage 1: String-based similarity (fast, language-agnostic)
        Stage 2: Entity-type compatibility check
        Stage 3: Embedding similarity (only for borderline cases)
        
        This approach avoids false positives from embedding model
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        emb = self._get_embedding(entity_name)
        if not emb:
            return []
        
        similar = []
        
        for known_name in self.extractor.known_entities:
            # Stage 1: Exact match
            if known_name.lower() == entity_name.lower():
                similar.append((known_name, 1.0, 'exact'))
                continue
            
            # Stage 1b: One is prefix/suffix of other
            if len(entity_name) > 2 and len(known_name) > 2:
                if known_name.startswith(entity_name) or entity_name.startswith(known_name):
                    similar.append((known_name, 0.95, 'prefix'))
                    continue
            
            # Stage 2: String-based similarity (language-agnostic)
            str_sim = self._string_similarity(entity_name, known_name)
            
            # If string similarity is very low, likely not similar
            if str_sim < 0.3:  # Less than 30% string similarity
                continue
            
            # Stage 3: Get entity types and check compatibility
            known_type = self.extractor.entity_types.get(known_name.lower(), 'concept')
            new_type = self.extractor.entity_types.get(entity_name.lower(), 'concept')
            
            # If types are incompatible, unlikely to be similar
            if not self._are_entity_types_compatible(known_type, new_type):
                continue
            
            # Stage 4: Embedding similarity (for borderline cases)
            known_emb = self._get_embedding(known_name)
            if not known_emb:
                continue
            
            # Cosine similarity
            dot = sum(a * b for a, b in zip(emb, known_emb))
            norm1 = sum(a * a for a in emb) ** 0.5
            norm2 = sum(b * b for b in known_emb) ** 0.5
            if norm1 > 0 and norm2 > 0:
                emb_sim = dot / (norm1 * norm2)
                
                # Combine string similarity and embedding similarity
                # Weight string similarity more for short names
                combined_sim = (str_sim * 0.6) + (emb_sim * 0.4)
                
                if combined_sim > threshold:
                    similar.append((known_name, combined_sim, 'combined'))
        
        similar.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in similar[:3]]
    
    def _create_entity_id(self, name: str) -> str:
        """Create a valid entity ID from name"""
        # Remove special chars, lowercase, hyphenate
        import unicodedata
        slug = name.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = slug[:50]
        return f"entity.auto-{slug}"
    
    def _suggest_relationship_type(self, entity_type: str, entity: Dict) -> str:
        """Suggest relationship type based on entity type"""
        type_to_rel = {
            'person': 'related_to',       # 人 → related_to
            'project': 'part_of',         # 項目 → part_of
            'company': 'uses',            # 公司 → uses (使用/合作)
            'location': 'located_in',     # 地點 → located_in
            'system': 'powers',           # 系統 → powers (為...提供動力)
            'technology': 'used_by',      # 技術 → used_by (被...使用)
            'concept': 'related_to',      # 概念 → related_to
        }
        return type_to_rel.get(entity_type, 'related_to')
    
    def _write_entity_file(self, name: str, entity_id: str, entity_type: str, relationships: List[Dict]) -> bool:
        """Write a new entity markdown file to the wiki"""
        try:
            # Convert wiki_path to Path object if needed
            wiki_path = Path(self.wiki_path) if isinstance(self.wiki_path, str) else self.wiki_path
            
            # Determine target directory
            entity_dir = wiki_path / 'ai-agent' / 'entities'
            entity_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename
            filename = f"{entity_id.replace('entity.auto-', '')}.md"
            filepath = entity_dir / filename
            
            # Build frontmatter
            import yaml
            fm = {
                'title': name,
                'type': 'entity',
                'confidence': 'auto-discovered',
                'auto_added': datetime.now().isoformat(),
                'entity_type': entity_type,
                'relationships': relationships,
            }
            
            # Build content
            content = '---\n'
            content += yaml.dump(fm, allow_unicode=True, default_flow_style=False)
            content += '---\n\n'
            content += f"# {name}\n\n"
            content += f"**Type:** {entity_type}\n\n"
            content += f"**Auto-discovered entity** from wiki analysis.\n\n"
            content += f"**Relationships:**\n"
            for rel in relationships:
                content += f"- {rel.get('type', 'related_to')}: {rel.get('target', 'unknown')}\n"
            
            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  📝 Created: {filepath.name}")
            return True
            
        except Exception as e:
            print(f"  ❌ Error writing {name}: {e}")
            return False
    
    def _add_entity_to_graph(self, name: str, entity_id: str, entity_type: str, relationships: List[Dict]) -> bool:
        """Add entity to the in-memory graph"""
        try:
            # Create GraphNode (note: path will be set when file is written)
            node = GraphNode(
                id=entity_id,
                name=name,
                entity_type=entity_type,
                path=f"ai-agent/entities/{entity_id.replace('entity.auto-', '')}.md",
                relationships=relationships,
                content_snippet=f"Auto-discovered entity: {name}",
            )
            
            # Add to nodes
            self.graph.nodes[entity_id] = node
            self.graph.entity_name_to_id[name.lower()] = entity_id
            
            # Add edges for relationships
            for rel in relationships:
                target = rel.get('target', '')
                rel_type = rel.get('type', 'related_to')
                
                # Find target node id
                target_id = self.graph.entity_name_to_id.get(target.lower())
                if not target_id:
                    # Try to find in nodes
                    for nid, n in self.graph.nodes.items():
                        if n.name.lower() == target.lower():
                            target_id = nid
                            break
                
                if target_id:
                    edge = GraphEdge(
                        from_id=entity_id,
                        to_id=target_id,
                        relationship_type=rel_type,
                        weight=1.0,
                    )
                    self.graph.edges.append(edge)
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error adding to graph: {e}")
            return False
    
    def _validate_entity(self, entity: Dict) -> bool:
        """Validate if entity meets quality thresholds"""
        if entity.get('confidence', 0) < self.min_confidence:
            return False
        
        name = entity.get('name', '')
        if len(name) < 2 or len(name) > 30:
            return False
        
        # Check it's not already in the graph
        if name in self.graph.nodes:
            return False
        
        return True
    
    def expand(self) -> Dict:
        """
        Perform auto-expansion of the Knowledge Graph.
        
        Returns:
            {
                'added_entities': [...],
                'added_relationships': [...],
                'stats': {...},
                'errors': [...]
            }
        """
        print("🔍 Scanning wiki for new entities...")
        
        # Extract entities and relationships
        extraction_result = self.extractor.scan_wiki()
        
        new_entities = extraction_result['new_entities']
        new_relationships = extraction_result['new_relationships']
        
        print(f"📊 Found {len(new_entities)} potential entities")
        print(f"📊 Found {len(new_relationships)} potential relationships")
        
        # Filter by confidence
        validated_entities = [e for e in new_entities if self._validate_entity(e)]
        print(f"✅ {len(validated_entities)} entities passed validation")
        
        # Pre-populate entity_types for validated entities (for cross-entity comparison)
        for e in validated_entities:
            self.extractor.entity_types[e['name'].lower()] = e.get('type', 'concept')
        
        # Process each entity
        for entity in validated_entities:
            try:
                name = entity['name']
                
                # Check for similar existing entities (unless disabled)
                if not self.skip_similarity_check:
                    similar = self._find_similar_entities(name)
                    if similar:
                        print(f"  ⚠️  '{name}' similar to {similar} - skipping (manual review needed)")
                        continue
                
                # Create entity ID
                entity_id = self._create_entity_id(name)
                
                # Determine relationship type based on entity type
                entity_type = entity.get('type', 'concept')
                relationship_type = self._suggest_relationship_type(entity_type, entity)
                
                # Build relationships list
                entity_relationships = [
                    {
                        'type': relationship_type,
                        'target': 'ocm-sup',
                        'direction': 'outgoing',
                    }
                ]
                
                # Add to in-memory graph (always)
                graph_success = self._add_entity_to_graph(
                    name=name,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    relationships=entity_relationships,
                )
                
                # Write entity file only if not dry-run
                file_success = True
                if not self.dry_run:
                    file_success = self._write_entity_file(
                        name=name,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        relationships=entity_relationships,
                    )
                
                if file_success:
                    self.added_entities.append({
                        'name': name,
                        'id': entity_id,
                        'type': entity_type,
                        'source': entity.get('source', 'unknown'),
                        'confidence': entity.get('confidence', 0),
                    })
                    if self.dry_run:
                        print(f"  ✅ Would add: {name} ({entity_type})")
                    else:
                        print(f"  ✅ Added: {name} ({entity_type})")
                
            except Exception as e:
                self.errors.append(f"Error adding {entity.get('name', 'unknown')}: {str(e)}")
        
        # Process relationships
        seen_rels = set()
        for rel in new_relationships:
            entity1, entity2, rel_type = rel
            
            # Check both entities exist in graph
            if entity1 in self.graph.nodes and entity2 in self.graph.nodes:
                rel_key = f"{entity1}:{rel_type}:{entity2}"
                if rel_key not in seen_rels:
                    seen_rels.add(rel_key)
                    
                    self.graph.add_relationship(
                        from_entity=entity1,
                        to_entity=entity2,
                        relationship_type=rel_type,
                    )
                    
                    self.added_relationships.append({
                        'from': entity1,
                        'to': entity2,
                        'type': rel_type,
                    })
        
        print(f"\n📈 Expansion Summary:")
        print(f"  Entities added: {len(self.added_entities)}")
        print(f"  Relationships added: {len(self.added_relationships)}")
        print(f"  Errors: {len(self.errors)}")
        
        return {
            'added_entities': self.added_entities,
            'added_relationships': self.added_relationships,
            'stats': {
                'total_found': len(new_entities),
                'validated': len(validated_entities),
                'added': len(self.added_entities),
                'relationships_added': len(self.added_relationships),
            },
            'errors': self.errors,
        }
    
    def save_changes(self):
        """Save the updated graph back to the entities"""
        self.graph.save_entities()
        print(f"💾 Graph changes saved to {self.graph.entity_dir}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='KG Auto-Expansion')
    parser.add_argument('--wiki-path', default='/root/.openclaw/workspace/wiki', help='Wiki path')
    parser.add_argument('--min-confidence', type=float, default=0.7, help='Minimum confidence threshold')
    parser.add_argument('--similarity-threshold', type=float, default=0.92, help='Similarity threshold (0.0-1.0, higher = stricter)')
    parser.add_argument('--no-similarity-check', action='store_true', help='Skip similarity check (add all validated entities)')
    parser.add_argument('--dry-run', action='store_true', help='Scan only, do not add entities')
    parser.add_argument('--save', action='store_true', help='Save changes to disk')
    
    args = parser.parse_args()
    
    print("🚀 KG Auto-Expansion System")
    print(f"   Wiki: {args.wiki_path}")
    print(f"   Min Confidence: {args.min_confidence}")
    print(f"   Similarity Threshold: {args.similarity_threshold}")
    print(f"   Skip Similarity Check: {args.no_similarity_check}")
    print(f"   Dry Run: {args.dry_run}")
    print()
    
    # Run expansion
    expander = KGAutoExpander(
        wiki_path=args.wiki_path,
        min_confidence=args.min_confidence,
        similarity_threshold=args.similarity_threshold,
        skip_similarity_check=args.no_similarity_check,
        dry_run=args.dry_run,
    )
    
    result = expander.expand()
    
    if args.dry_run:
        print("\n🔍 Dry run - no changes saved")
        print(f"Would add {len(result['added_entities'])} entities")
        print(f"Would add {len(result['added_relationships'])} relationships")
    elif args.save:
        expander.save_changes()
        print("\n💾 Changes saved to disk")
    
    # Output JSON for piping
    import json
    print("\n📤 JSON Output:")
    print(json.dumps({
        'added_entities': result['added_entities'],
        'added_relationships': result['added_relationships'],
        'stats': result['stats'],
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()