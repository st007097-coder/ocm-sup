#!/usr/bin/env python3
"""
Triple-Stream Enhanced Search
BM25 + Vector + Graph with RRF Fusion + Query Expansion

OCM Sup Enhanced Search Architecture v2
"""

import json
import time
import os
import re
import hashlib
import yaml
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import numpy as np

# BM25
from rank_bm25 import BM25Okapi

# Ollama
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Query expansion
from query_expansion import QueryExpander

# Graph search
from graph_search import GraphSearchChannel

from enum import Enum


class QueryIntent(Enum):
    ENTITY = "entity"           # Exact entity name (期哥, 古洞站, OpenClaw)
    CONCEPT = "concept"         # Concept name (BM25, RRF, Query Expansion)
    CONTENT = "content"         # Content search (longer descriptive queries)
    AMBIGUOUS = "ambiguous"      # Could be multiple things (QS, agent)
    CROSS_LINGUAL = "cross_lingual"  # Mixed language
    TOOL = "tool"               # Tool name (Tavily, Obsidian)


# Known entities (exact names) - used for intent classification
KNOWN_ENTITIES = {
    "期哥", "Jacky", "阿星", "古洞站", "OpenClaw", "Tavily", "Obsidian",
    "Hermes", "Knowledge Graph", "BM25", "RRF", "Consolidation Loop",
    "Latency Benchmark", "Quantity Surveyor", "Query Expansion", "Tavily",
    "Triple-Stream Search", "Vector Search", "Lossless-Claw", "OCM Sup",
    "Memory System", "GBrain-Lite", "Mr. Black",
}


class EmbeddingCache:
    """Cache document embeddings"""

    def __init__(self, cache_path: str = "/root/.openclaw/scripts/.embeddings_cache.json"):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = __import__('threading').Lock()
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        with self._lock:
            with open(self.cache_path, 'w') as f:
                json.dump(self._cache, f, indent=2)

    def get(self, doc_path: str, doc_hash: str) -> Optional[List[float]]:
        key = f"{doc_path}:{doc_hash}"
        cached = self._cache.get(key)
        if cached and len(cached) == 768:
            return cached
        return None

    def set(self, doc_path: str, doc_hash: str, embedding: List[float]):
        key = f"{doc_path}:{doc_hash}"
        self._cache[key] = embedding
        if len(self._cache) % 10 == 0:
            self._save_cache()

    def save(self):
        self._save_cache()


class TripleStreamSearch:
    """
    Triple-Stream Enhanced Search

    Architecture:
    Query → BM25 Channel ─┐
         → Vector Channel ─┼→ RRF Fusion → Results
         → Graph Channel ──┘
              ↑
         Query Expansion (pre-processing)
    """

    def __init__(
        self,
        wiki_path: str = "/root/.openclaw/workspace/wiki",
        ollama_url: str = "http://host.docker.internal:11434",
        embedding_model: str = "nomic-embed-text:latest",
        rrf_k: int = 60,
        token_budget: int = 2000,
        max_workers: int = 5,
        graph_max_depth: int = 2,
    ):
        self.wiki_path = Path(wiki_path)
        self.ollama_url = ollama_url
        self.embedding_model = embedding_model
        self.rrf_k = rrf_k
        self.token_budget = token_budget
        self.max_workers = max_workers
        self.graph_max_depth = graph_max_depth

        # Query expander
        self.expander = QueryExpander()

        # BM25 components
        self.bm25_documents: List[str] = []
        self.bm25_tokenized: List[List[str]] = []
        self.bm25_metadata: List[Dict] = []
        self.bm25_index: Optional[BM25Okapi] = None

        # Vector components (lazy loaded on first search)
        self.vector_documents: List[str] = []
        self.vector_embeddings: Optional[np.ndarray] = None
        self.vector_metadata: List[Dict] = []
        self._vector_loaded: bool = False
        self._vector_load_lock = threading.Lock()

        # Graph channel
        self.graph_channel: Optional[GraphSearchChannel] = None

        # Cache
        self.cache = EmbeddingCache()

        # Initialize BM25 + Graph (fast)
        self._load_documents()
        self._build_bm25_index()
        self._init_graph_channel()
        # Vector embeddings are LAZY loaded on first search

    def _compute_hash(self, content: str) -> str:
        return hashlib.md5(content[:5000].encode()).hexdigest()

    def _tokenize(self, text: str) -> List[str]:
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        tokens = text.split()
        return [t.lower() if not re.search(r'[\u4e00-\u9fff]', t) else t for t in tokens if t.strip()]

    def _extract_title(self, content: str, filepath: Path) -> str:
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            title_match = re.search(r'^title:\s*(.+?)\s*$', match.group(1), re.MULTILINE)
            if title_match:
                return title_match.group(1).strip()

        heading_match = re.search(r'^#\s+(.+?)\s*$', content, re.MULTILINE)
        if heading_match:
            return heading_match.group(1).strip()

        return filepath.stem

    def _extract_plain_text(self, content: str) -> str:
        text = re.sub(r'^---\n.*?\n---\n?', '', content, flags=re.DOTALL)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
        text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        return text

    def _load_documents(self):
        markdown_extensions = {'.md', '.markdown'}

        for root, dirs, files in os.walk(self.wiki_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if any(file.endswith(ext) for ext in markdown_extensions):
                    filepath = Path(root) / file

                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        title = self._extract_title(content, filepath)
                        plain_text = self._extract_plain_text(content)

                        if plain_text.strip():
                            rel_path = str(filepath.relative_to(self.wiki_path))
                            doc_hash = self._compute_hash(content)

                            self.bm25_documents.append(plain_text)
                            self.bm25_tokenized.append(self._tokenize(plain_text))
                            self.bm25_metadata.append({
                                'title': title,
                                'path': rel_path,
                                'full_path': str(filepath),
                                'hash': doc_hash,
                            })

                            self.vector_documents.append(plain_text)
                            self.vector_metadata.append({
                                'title': title,
                                'path': rel_path,
                                'full_path': str(filepath),
                                'hash': doc_hash,
                            })
                    except:
                        pass

        # print(f"Loaded {len(self.bm25_documents)} documents")

    def _build_bm25_index(self):
        if self.bm25_tokenized:
            self.bm25_index = BM25Okapi(self.bm25_tokenized)
            # print(f"Built BM25 index with {len(self.bm25_tokenized)} documents")

    def _get_embedding(self, doc_text: str, doc_path: str, doc_hash: str) -> Optional[np.ndarray]:
        cached = self.cache.get(doc_path, doc_hash)
        if cached:
            return np.array(cached)

        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": doc_text[:2000]},
                timeout=30
            )

            if response.status_code == 200:
                emb = response.json().get('embedding', [])
                if emb:
                    self.cache.set(doc_path, doc_hash, emb)
                    return np.array(emb)
        except:
            pass

        return None

    def _ensure_vector_loaded(self):
        """"Lazy load vector embeddings on first search call (thread-safe)"""
        if self._vector_loaded:
            return
        with self._vector_load_lock:
            if self._vector_loaded:
                return
            # print("Lazy loading vector embeddings...")
            self._load_embeddings_parallel()
            self._vector_loaded = True

    def _load_embeddings_parallel(self):
        embeddings = [None] * len(self.vector_documents)
        uncached_indices = [
            i for i, m in enumerate(self.vector_metadata)
            if not self.cache.get(m['full_path'], m['hash'])
        ]

        # Limit to first 50 uncached docs to avoid long blocking
        # Rest will have zero vector scores but BM25+Graph will still work
        MAX_NEW_EMBEDDINGS = 50
        uncached_to_compute = uncached_indices[:MAX_NEW_EMBEDDINGS]
        # Mark rest as already failed/skipped by leaving embeddings[idx]=None

        def fetch_embedding(idx):
            m = self.vector_metadata[idx]
            emb = self._get_embedding(
                self.vector_documents[idx],
                m['full_path'],
                m['hash']
            )
            return idx, emb

        if uncached_to_compute:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(fetch_embedding, idx): idx
                    for idx in uncached_to_compute
                }

                for future in as_completed(futures):
                    idx, emb = future.result()
                    if emb is not None:
                        embeddings[idx] = emb

        # Fill cached (this is fast - just reading from dict)
        for i in range(len(embeddings)):
            if embeddings[i] is None:
                cached = self.cache.get(
                    self.vector_metadata[i]['full_path'],
                    self.vector_metadata[i]['hash']
                )
                if cached:
                    embeddings[i] = np.array(cached)

        valid_embeddings = [e for e in embeddings if e is not None]

        if valid_embeddings:
            self.vector_embeddings = np.array(valid_embeddings)

    def _init_graph_channel(self):
        """Initialize the graph search channel"""
        self.graph_channel = GraphSearchChannel(str(self.wiki_path))
        # print(f"Graph channel initialized: {self.graph_channel.get_stats()}")

    def _get_query_embedding(self, query: str) -> Optional[np.ndarray]:
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": query[:500]},
                timeout=30
            )

            if response.status_code == 200:
                return np.array(response.json().get('embedding', []))
        except:
            pass

        return None

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def search_bm25_expanded(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """BM25 search with query expansion"""
        expanded_query, variants = self.expander.expand_query(query, max_expansions=5)

        combined_scores: Dict[int, float] = defaultdict(float)
        variant_counts: Dict[int, int] = defaultdict(int)

        for variant in variants[:5]:
            tokenized_query = self._tokenize(variant)
            if not tokenized_query:
                continue

            scores = self.bm25_index.get_scores(tokenized_query)

            for doc_idx, score in enumerate(scores):
                if score > 0:
                    combined_scores[doc_idx] += score
                    variant_counts[doc_idx] += 1

        # Average scores
        averaged = [
            (doc_idx, score / max(variant_counts[doc_idx], 1))
            for doc_idx, score in combined_scores.items()
        ]

        averaged.sort(key=lambda x: x[1], reverse=True)

        return averaged[:top_k]

    def search_vector(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """Vector similarity search (lazy loads on first call)"""
        import threading
        
        # Threading-based timeout for vector loading
        result = {'loaded': False, 'error': None}
        
        def load_vectors():
            try:
                self._ensure_vector_loaded()
                result['loaded'] = True
            except Exception as e:
                result['error'] = str(e)
        
        t = threading.Thread(target=load_vectors)
        t.daemon = True
        t.start()
        t.join(timeout=15)  # 15 second timeout
        
        if t.is_alive() or not result['loaded']:
            # Loading timed out or failed - return empty, BM25+Graph will handle search
            return []
        
        if self.vector_embeddings is None:
            return []

        query_emb = self._get_query_embedding(query)
        if query_emb is None:
            return []

        similarities = []
        for i in range(len(self.vector_embeddings)):
            sim = self._cosine_similarity(query_emb, self.vector_embeddings[i])
            similarities.append((i, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def search_graph(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """Graph-based search through entity relationships"""
        if self.graph_channel is None:
            return []

        graph_results = self.graph_channel.search_by_entities(query, max_depth=self.graph_max_depth)

        # Map graph results to document indices
        results = []
        for result in graph_results:
            # Find matching document index
            path = result['path']
            for doc_idx, metadata in enumerate(self.bm25_metadata):
                if metadata['path'] == path:
                    results.append((doc_idx, result['score']))
                    break

        return results[:top_k]

    def rrf_fusion(
        self,
        bm25_results: List[Tuple[int, float]],
        vector_results: List[Tuple[int, float]],
        graph_results: List[Tuple[int, float]],
        k: int = 60
    ) -> List[Tuple[int, float]]:
        """Triple RRF Fusion: BM25 + Vector + Graph

        P1.2 Relevance Ranking improvement (2026-04-22):
        - BM25 weight: 1.5 (up from 1.0) - exact/keyword matches are most reliable
        - Vector weight: 1.0 - semantic similarity for fuzzy matches
        - Graph weight: 0.8 (down from 1.5) - relationships can be noisy
        """
        scores = defaultdict(float)

        # BM25 contributions (weight: 1.5 - higher because exact/keyword matches are most reliable)
        for rank, (doc_idx, score) in enumerate(bm25_results):
            scores[doc_idx] += 1.5 / (k + rank + 1)

        # Vector contributions (weight: 1.0 - semantic similarity, good for fuzzy matches)
        for rank, (doc_idx, score) in enumerate(vector_results):
            scores[doc_idx] += 1.0 / (k + rank + 1)

        # Graph contributions (weight: 0.8 - relationship-based, can be noisy)
        for rank, (doc_idx, score) in enumerate(graph_results):
            scores[doc_idx] += 0.8 / (k + rank + 1)

        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return [(doc_idx, score) for doc_idx, score in sorted_results]

    def _classify_query(self, query: str) -> Tuple[QueryIntent, Dict]:
        """Classify query intent for adaptive ranking.

        P2: Query Intent Classification (2026-04-22)
        """
        query = query.strip()
        query_lower = query.lower()

        has_chinese = bool(re.search(r'[\u4e00-\uffff]', query))
        has_english = bool(re.search(r'[a-zA-Z]', query))

        # Check if it's a known entity
        if query in KNOWN_ENTITIES or query_lower in [e.lower() for e in KNOWN_ENTITIES]:
            return QueryIntent.ENTITY, {"matched_entity": query}

        # Check for ambiguous terms (multiple interpretations)
        if query in {"QS", "qs", "Agent", "agent", "Memory", "memory"}:
            return QueryIntent.AMBIGUOUS, {"interpretations": ["varies"]}

        # Check for cross-lingual (mixed Chinese and English)
        if has_chinese and has_english:
            return QueryIntent.CROSS_LINGUAL, {"has_chinese": True, "has_english": True}

        # Check for short technical queries (likely concepts)
        if len(query.split()) <= 3:
            technical_terms = ["bm25", "rrf", "search", "query", "expansion",
                            "fusion", "graph", "vector", "embedding", "memory"]
            if any(term in query_lower for term in technical_terms):
                return QueryIntent.CONCEPT, {}

        # Check for tool-like queries
        tools = ["tavily", "obsidian", "notion", "telegram", "github", "gmail", "win32"]
        if any(tool in query_lower for tool in tools):
            return QueryIntent.TOOL, {}

        # Default: content search (longer descriptive queries)
        if len(query.split()) > 4:
            return QueryIntent.CONTENT, {}

        # Short queries default to concept
        return QueryIntent.CONCEPT, {}

    def _intent_adaptive_rff(
        self,
        query: str,
        bm25_results: List[Tuple[int, float]],
        vector_results: List[Tuple[int, float]],
        graph_results: List[Tuple[int, float]],
        k: int = 60
    ) -> List[Tuple[int, float]]:
        """"RRF with intent-adaptive weights.

        P2: Query Intent Classification (2026-04-22)
        """
        intent, meta = self._classify_query(query)

        # Intent-adaptive weights
        weights_map = {
            QueryIntent.ENTITY:        {"bm25": 2.0, "vector": 0.5, "graph": 1.0},
            QueryIntent.CONCEPT:       {"bm25": 1.5, "vector": 1.0, "graph": 0.8},
            QueryIntent.CONTENT:       {"bm25": 1.0, "vector": 1.5, "graph": 0.5},
            QueryIntent.AMBIGUOUS:     {"bm25": 1.5, "vector": 1.0, "graph": 1.0},
            QueryIntent.CROSS_LINGUAL: {"bm25": 2.0, "vector": 0.8, "graph": 0.5},
            QueryIntent.TOOL:          {"bm25": 1.5, "vector": 0.8, "graph": 1.2},
        }
        weights = weights_map.get(intent, {"bm25": 1.5, "vector": 1.0, "graph": 0.8})

        scores = defaultdict(float)

        # BM25 contributions
        for rank, (doc_idx, _) in enumerate(bm25_results):
            scores[doc_idx] += weights["bm25"] / (k + rank + 1)

        # Vector contributions
        for rank, (doc_idx, _) in enumerate(vector_results):
            scores[doc_idx] += weights["vector"] / (k + rank + 1)

        # Graph contributions
        for rank, (doc_idx, _) in enumerate(graph_results):
            scores[doc_idx] += weights["graph"] / (k + rank + 1)

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def _is_substring_match(self, query: str, title: str) -> bool:
        """Check if query is a meaningful substring/prefix of title."""
        query_lower = query.lower().strip()
        title_lower = title.lower().strip()

        # Query is prefix of title (e.g., "Triple-Stream" in "Triple-Stream Search")
        if title_lower.startswith(query_lower):
            return True

        # Query is substring of title with significant word boundary
        if query_lower in title_lower:
            # Check if it's a word-boundary match (not just random substring)
            idx = title_lower.find(query_lower)
            if idx == 0 or title_lower[idx-1] in ' _-':
                return True

        return False

    def _exact_match_boost(
        self,
        query: str,
        bm25_results: List[Tuple[int, float]],
        vector_results: List[Tuple[int, float]],
        boost_factor: float = 50.0
    ) -> Tuple[List[Tuple[int, float]], Dict]:
        """
        When query matches an entity title, ensure that entity ranks FIRST.

        Priority:
        1. Exact match (query == title)
        2. Normalized exact match (ignoring spaces/hyphens)
        3. Substring/prefix match (query is prefix/substring of title)
        4. If not found in BM25 results, search ALL documents
        """
        if not query or not bm25_results:
            return bm25_results, {}

        query_lower = query.lower().strip()
        query_normalized = query_lower.replace(' ', '').replace('-', '')
        boost_info = {'query': query, 'boosted': False, 'boosted_doc_idx': None, 'boosted_title': None}

        # Find exact match - first in BM25 results
        # P0.5 Fix: Entity Path Priority for Exact Match Selection
        # When multiple entities match the query (e.g., 期哥 appears in multiple paths),
        # prefer by path priority instead of just BM25 score
        # Priority: ai-agent/entities > knowledge/entities > originals > others
        def get_entity_priority(doc_idx: int) -> int:
            """Lower is better priority. Returns tuple (priority, -score) for sorting."""
            metadata = self.bm25_metadata[doc_idx]
            path = metadata.get('path', '').lower()
            bm25_score = metadata.get('score', 0)  # Original BM25 score
            
            # Priority 1: ai-agent/entities (core entities)
            if '/ai-agent/entities/' in path:
                return (1, -bm25_score)
            # Priority 2: knowledge/entities (knowledge base entities)
            elif '/knowledge/entities/' in path:
                return (2, -bm25_score)
            # Priority 3: content/originals/ (originals capture)
            elif '/content/originals/' in path:
                return (3, -bm25_score)
            # Priority 4: other entities (health, education, etc.)
            elif '/entities/' in path:
                return (4, -bm25_score)
            # Priority 5: sources
            elif '/sources/' in path:
                return (5, -bm25_score)
            # Priority 6: everything else
            else:
                return (6, -bm25_score)

        exact_match_idx = None
        exact_match_metadata = None
        exact_match_type = None

        # P0.5 Bug Fix: Exact matches should be searched in ALL documents FIRST
        # before substring matches in BM25 results.
        # Reason: doc_idx=182 "OpenClaw" has BM25 score 0.0 (content doesn't contain "openclaw")
        # so it's not in top-k BM25 results. Substring matching then incorrectly picks
        # doc_idx=157 "Hermes vs OpenClaw" which IS in top-k BM25 results.
        # Fix: Search exact matches in ALL documents first (not just top-k), regardless of BM25 score.
        
        # Step 1: Search EXACT matches in ALL documents (not just BM25 results)
        exact_matches = []
        for doc_idx, metadata in enumerate(self.bm25_metadata):
            title = metadata.get('title', '').lower().strip()
            title_normalized = title.replace(' ', '').replace('-', '')

            # Check for exact match (case-insensitive, ignoring spaces/hyphens)
            if title == query_lower or title_normalized == query_normalized:
                exact_matches.append((doc_idx, metadata, 'exact_all', get_entity_priority(doc_idx)))

        # Step 2: If no exact matches found, search SUBSTRING matches in BM25 results
        substring_matches = []
        if not exact_matches:
            for doc_idx, _ in bm25_results:
                metadata = self.bm25_metadata[doc_idx]
                title = metadata.get('title', '').lower().strip()
                if self._is_substring_match(query_lower, title):
                    substring_matches.append((doc_idx, metadata, 'substring', get_entity_priority(doc_idx)))

        # Use exact matches if found, otherwise use substring matches
        all_matches = exact_matches if exact_matches else substring_matches

        # Select best match by priority (lowest priority number wins)
        # Select best match by priority from all matches (exact matches preferred, then substring)
        if all_matches:
            # Sort by priority tuple (priority, then -bm25_score for same priority)
            all_matches.sort(key=lambda x: x[3])
            exact_match_idx, exact_match_metadata, exact_match_type, _ = all_matches[0]
            boost_info['boosted'] = True
            boost_info['boosted_doc_idx'] = exact_match_idx
            boost_info['boosted_title'] = exact_match_metadata.get('title', '')
            boost_info['match_type'] = exact_match_type


        if exact_match_idx is None:
            return bm25_results, boost_info

        # REORDER: Put exact match at the top with maximum score
        boosted_bm25 = []

        # Add exact match first with very high score
        boosted_bm25.append((exact_match_idx, 10000.0))

        # Add all other results with original scores (except exact match)
        for doc_idx, score in bm25_results:
            if doc_idx != exact_match_idx:
                boosted_bm25.append((doc_idx, score))

        return boosted_bm25, boost_info

    def _exact_match_graph_boost(
        self,
        query: str,
        graph_results: List[Tuple[int, float]],
        boost_info: Dict = None
    ) -> List[Tuple[int, float]]:
        """
        Boost exact entity match in Graph results.

        If BM25 already found an exact match (boost_info['boosted'] is True),
        skip Graph boost to avoid duplicate boosting and RRF confusion.
        """
        if not query or not graph_results:
            return graph_results

        # Skip Graph exact match boost if BM25 already found exact match
        # This prevents duplicate boosting (BM25=10000 + Graph=10000) which confuses RRF
        if boost_info and boost_info.get('boosted') and boost_info.get('boosted_doc_idx') is not None:
            # BM25 already boosted the exact match - skip Graph boost to avoid RRF pollution
            return graph_results

        query_lower = query.lower().strip()
        query_normalized = query_lower.replace(' ', '').replace('-', '')

        # Find best match in BM25 metadata
        best_doc_idx = None
        best_match_type = None  # 'exact', 'normalized', or 'substring'

        for doc_idx, _ in graph_results:
            metadata = self.bm25_metadata[doc_idx]
            title = metadata.get('title', '').lower().strip()
            title_normalized = title.replace(' ', '').replace('-', '')

            # Check for exact match first
            if title == query_lower:
                best_doc_idx = doc_idx
                best_match_type = 'exact'
                break

            # Check for normalized exact match (ignoring spaces/hyphens)
            if title_normalized == query_normalized and best_match_type != 'exact':
                best_doc_idx = doc_idx
                best_match_type = 'normalized'

        # If no exact/normalized match found, try substring match in graph results
        if best_doc_idx is None:
            for doc_idx, _ in graph_results:
                metadata = self.bm25_metadata[doc_idx]
                title = metadata.get('title', '').lower().strip()

                if self._is_substring_match(query_lower, title):
                    best_doc_idx = doc_idx
                    best_match_type = 'substring'
                    break

        # If still not found, search ALL documents
        if best_doc_idx is None:
            for doc_idx, metadata in enumerate(self.bm25_metadata):
                title = metadata.get('title', '').lower().strip()
                title_normalized = title.replace(' ', '').replace('-', '')

                if title == query_lower:
                    best_doc_idx = doc_idx
                    best_match_type = 'exact'
                    break
                elif title_normalized == query_normalized and best_match_type != 'exact':
                    best_doc_idx = doc_idx
                    best_match_type = 'normalized'
                elif best_doc_idx is None and self._is_substring_match(query_lower, title):
                    best_doc_idx = doc_idx
                    best_match_type = 'substring'

        if best_doc_idx is None:
            return graph_results

        # Now boost the best match to the top of graph_results
        boosted = []
        best_found = False

        for doc_idx, score in graph_results:
            if doc_idx == best_doc_idx and not best_found:
                boosted.append((doc_idx, 10000.0))
                best_found = True
            else:
                boosted.append((doc_idx, score))

        # If the best match wasn't in graph_results, prepend it
        if not best_found and best_doc_idx is not None:
            boosted.insert(0, (best_doc_idx, 10000.0))

        return boosted
    
    def _query_time_entity_expansion(
        self,
        boost_info: Dict,
        bm25_results: List[Tuple[int, float]],
        vector_results: List[Tuple[int, float]],
        graph_results: List[Tuple[int, float]],
        community_boost_factor: float = 1.5
    ) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]], List[Tuple[int, float]], Dict]:
        """
        P3.B: Query-Time Entity Expansion
        
        When query matches an entity exactly, automatically include and boost
        community members in the search results.
        
        This provides richer context by showing related entities that share
        the same community (detected via Louvain).
        """
        expansion_info = {
            'expanded': False,
            'exact_match_title': None,
            'community_members_added': [],
            'community_id': None
        }
        
        # Check if there was an exact match
        if not boost_info.get('boosted') or boost_info.get('boosted_doc_idx') is None:
            return bm25_results, vector_results, graph_results, expansion_info
        
        exact_doc_idx = boost_info['boosted_doc_idx']
        exact_metadata = self.bm25_metadata[exact_doc_idx]
        exact_path = exact_metadata.get('path', '')
        
        # Look up entity from path
        if self.graph_channel is None:
            return bm25_results, vector_results, graph_results, expansion_info
        
        entity_id = self.graph_channel.path_to_entity_id.get(exact_path)
        if entity_id is None:
            return bm25_results, vector_results, graph_results, expansion_info
        
        # Get community info
        community_id = self.graph_channel.get_entity_community(entity_id)
        if community_id is None:
            return bm25_results, vector_results, graph_results, expansion_info
        
        # Get community members
        community_members = self.graph_channel.get_related_in_community(entity_id)
        if not community_members:
            return bm25_results, vector_results, graph_results, expansion_info
        
        expansion_info['expanded'] = True
        expansion_info['exact_match_title'] = boost_info.get('boosted_title')
        expansion_info['community_id'] = community_id
        
        # Build mapping: community member name -> doc_idx
        # Deduplicate community members by name to avoid duplicates in results and expansion_info
        # Cap at MAX_COMMUNITY_MEMBERS to avoid flooding results
        # Exclude the source entity (exact match) from being added via community expansion
        MAX_COMMUNITY_MEMBERS = 5
        member_to_doc_idx = {}
        seen_member_names = set()
        for doc_idx, metadata in enumerate(self.bm25_metadata):
            if len(member_to_doc_idx) >= MAX_COMMUNITY_MEMBERS:
                break
            title_lower = metadata.get('title', '').lower()
            title_normalized = title_lower.replace(' ', '').replace('-', '')
            query_lower = boost_info.get('query', '').lower().strip()
            query_normalized = query_lower.replace(' ', '').replace('-', '')
            # Skip if this is the source entity itself (exact match)
            if title_lower == query_lower or title_normalized == query_normalized:
                continue
            for member in community_members:
                if len(member_to_doc_idx) >= MAX_COMMUNITY_MEMBERS:
                    break
                member_name_lower = member['name'].lower()
                if title_lower == member_name_lower and member_name_lower not in seen_member_names:
                    seen_member_names.add(member_name_lower)
                    member_to_doc_idx[member['name']] = doc_idx
                    expansion_info['community_members_added'].append(member['name'])
        
        # Add community members to all search channels with boost
        community_doc_indices = set(member_to_doc_idx.values())
        
        # Helper function to add community members with boost
        def add_community_boost(results: List[Tuple[int, float]], boost_factor: float) -> List[Tuple[int, float]]:
            if not results:
                return results
            
            # Get existing doc indices
            existing_indices = {doc_idx for doc_idx, _ in results}
            
            # Add community members not already in results
            augmented = list(results)
            for member_name, doc_idx in member_to_doc_idx.items():
                if doc_idx not in existing_indices:
                    # Add with moderate score (boosted)
                    augmented.append((doc_idx, 5.0 * boost_factor))
            
            return augmented
        
        # Apply community boost to all channels
        bm25_results = add_community_boost(bm25_results, community_boost_factor)
        vector_results = add_community_boost(vector_results, community_boost_factor)
        graph_results = add_community_boost(graph_results, community_boost_factor)
        
        return bm25_results, vector_results, graph_results, expansion_info
    
    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Dict]:
        """Triple-stream search with all channels"""
        # BM25 search (with query expansion)
        bm25_results = self.search_bm25_expanded(query, top_k * 2)

        # Vector search
        vector_results = self.search_vector(query, top_k * 2)

        # Graph search
        graph_results = self.search_graph(query, top_k * 2)

        # P0.3 Fix: Exact Match Boost
        # When query exactly matches an entity title, ensure that entity ranks FIRST
        # This fixes the Graph false positive problem (93% -> lower)
        bm25_results, boost_info = self._exact_match_boost(query, bm25_results, vector_results)

        # Also boost exact match in Graph results if BM25 didn't find it
        # Pass boost_info so Graph skip if BM25 already found exact match
        graph_results = self._exact_match_graph_boost(query, graph_results, boost_info)
        
        # P3.B: Query-Time Entity Expansion DISABLED (2026-04-22)
        # Bug: Community detection groups 期哥 with 300+ medical documents, causing pollution
        # Re-enable once community detection bug is fixed
        expansion_info = {}  # Placeholder when P3.B is disabled
        # bm25_results, vector_results, graph_results, expansion_info = self._query_time_entity_expansion(
        #     boost_info, bm25_results, vector_results, graph_results
        # )
        
        # Triple RRF fusion (P2: intent-adaptive weights)
        fused_results = self._intent_adaptive_rff(query, bm25_results, vector_results, graph_results, self.rrf_k)
        top_results = fused_results[:top_k]

        # Build response
        response = []
        for doc_idx, rrf_score in top_results:
            metadata = self.bm25_metadata[doc_idx]

            bm25_score = next(
                (s for i, s in bm25_results if i == doc_idx),
                0.0
            )
            vector_score = next(
                (s for i, s in vector_results if i == doc_idx),
                0.0
            )
            graph_score = next(
                (s for i, s in graph_results if i == doc_idx),
                0.0
            )

            sources = self._get_sources(bm25_score, vector_score, graph_score)

            # P3.A: Add community context to search results
            community_info = self._get_community_context(metadata.get('path', ''))

            response.append({
                'title': metadata['title'],
                'path': metadata['path'],
                'rrf_score': rrf_score,
                'bm25_score': bm25_score,
                'vector_score': vector_score,
                'graph_score': graph_score,
                'sources': sources,
                'expansion': self.expander.expand_query(query)[1][:3],
                **community_info,  # P3.A: community_id, community_members
                **expansion_info,  # P3.B: query_time_expansion info
            })

        # Update lastAccessed for all returned documents
        today = datetime.now().strftime('%Y-%m-%d')
        for result in response:
            self._update_last_accessed(result['path'], today)
            self._decay_confidence(result['path'])

        return response

    def _update_last_accessed(self, path: str, date: str, thread_lock=None):
        """"Update lastAccessed field in a wiki file's frontmatter."""
        try:
            # Resolve relative paths against wiki directory
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.wiki_path / path
            if not file_path.exists():
                return
            content = file_path.read_text()

            # Check if lastAccessed already set to this date
            if re.search(r'^lastAccessed:\s*' + date, content, re.MULTILINE):
                return

            # Update or add lastAccessed
            if re.search(r'^lastAccessed:', content, re.MULTILINE):
                content = re.sub(
                    r'^lastAccessed:\s*.+$',
                    f'lastAccessed: {date}',
                    content,
                    flags=re.MULTILINE
                )
            else:
                # Add after confidence: field (insert approach)
                content = re.sub(
                    r'^(confidence:.+)',
                    rf'\1\nlastAccessed: {date}',
                    content,
                    flags=re.MULTILINE
                )

            file_path.write_text(content)
        except Exception:
            pass  # Silently fail - don't disrupt search

    def _get_sources(self, bm25_score: float, vector_score: float, graph_score: float) -> List[str]:
        sources = []
        if bm25_score > 0:
            sources.append('bm25')
        if vector_score > 0.1:
            sources.append('vector')
        if graph_score > 0:
            sources.append('graph')
        return sources if sources else ['none']

    def _get_community_context(self, path: str) -> Dict:
        """Get community context for a search result.

        P3.A: Add community context to search results
        - Finds the entity that corresponds to the result path
        - Returns community_id and up to 5 related members in same community
        """
        if self.graph_channel is None:
            return {'community_id': None, 'community_members': []}

        # Find entity by path
        entity_id = self.graph_channel.path_to_entity_id.get(path)
        if entity_id is None:
            return {'community_id': None, 'community_members': []}

        # Get community
        community_id = self.graph_channel.get_entity_community(entity_id)
        if community_id is None:
            return {'community_id': None, 'community_members': []}

        # Get community members (up to 5, excluding self)
        members = self.graph_channel.get_related_in_community(entity_id)[:5]

        return {
            'community_id': community_id,
            'community_members': members
        }

    def _decay_confidence(self, path: str, decay: float = 0.02) -> bool:
        """Decay confidence of a wiki page on search hit.

        "Use it or lose it" mechanism: pages that appear in search results
        get slightly lower confidence each time they're accessed.
        This incentivizes fresh content and prevents stale pages from
        permanently ranking high.

        Args:
            path: Path to wiki file
            decay: Amount to decay confidence by (default 0.02 = 2%)

        Returns:
            True if confidence was updated, False otherwise
        """
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.wiki_path / path
            if not file_path.exists():
                return False

            content = file_path.read_text()

            # Find current confidence
            conf_match = re.search(r'^confidence:\s*([0-9.]+)', content, re.MULTILINE)
            if not conf_match:
                return False

            current_conf = float(conf_match.group(1))

            # Apply decay (minimum 0.1 to avoid total collapse)
            new_conf = max(0.1, current_conf - decay)

            # Only update if change is meaningful (>0.01)
            if abs(new_conf - current_conf) < 0.01:
                return False

            # Update confidence
            content = re.sub(
                r'^confidence:\s*[0-9.]+',
                f'confidence: {new_conf:.2f}',
                content,
                flags=re.MULTILINE
            )

            file_path.write_text(content)
            return True
        except Exception:
            return False

    def save_cache(self):
        self.cache.save()
        print("Cache saved")

    def get_stats(self) -> Dict:
        stats = {
            'document_count': len(self.bm25_documents),
            'bm25_indexed': self.bm25_index is not None,
            'vector_loaded': self.vector_embeddings is not None,
            'vector_shape': self.vector_embeddings.shape if self.vector_embeddings is not None else None,
            'cache_size': len(self.cache._cache),
            'rrf_k': self.rrf_k,
        }

        if self.graph_channel:
            graph_stats = self.graph_channel.get_stats()
            stats['graph_entities'] = graph_stats['entity_count']
            stats['graph_edges'] = graph_stats['edge_count']

        return stats


def main():
    print("🧪 Triple-Stream Enhanced Search")
    print("=" * 60)

    wiki_path = "/root/.openclaw/workspace/wiki"
    search = TripleStreamSearch(wiki_path=wiki_path)

    stats = search.get_stats()
    print(f"\n📊 System Stats:")
    for k, v in stats.items():
        print(f"   {k}: {v}")

    # Test queries
    test_queries = [
        "古洞站",
        "期哥",
        "阿星",
        "知識圖譜",
        "OCM Sup",
        "AI助手",
    ]

    print(f"\n🔍 Test Triple-Stream Searches:")
    for query in test_queries:
        print(f"\n   Query: {query}")

        start = time.time()
        results = search.search(query, top_k=5)
        elapsed = (time.time() - start) * 1000

        if results:
            print(f"   ⏱️  {elapsed:.0f}ms | {len(results)} results")
            for i, r in enumerate(results, 1):
                sources = '+'.join(r['sources'])
                print(f"   {i}. [{sources}] {r['title']}")
                print(f"      RRF={r['rrf_score']:.3f} BM25={r['bm25_score']:.2f} Vec={r['vector_score']:.3f} Graph={r['graph_score']:.2f}")
        else:
            print(f"   ❌ No results")

    search.save_cache()
    print("\n✅ Triple-Stream Search test complete")


if __name__ == "__main__":
    main()