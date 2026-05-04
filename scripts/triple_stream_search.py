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
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

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


class EmbeddingCache:
    """Cache document embeddings"""
    
    def __init__(self, cache_path: str = "/home/jacky/.openclaw/scripts/.embeddings_cache.json"):
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
        wiki_path: str = "/home/jacky/.openclaw/workspace/wiki",
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
        
        # Vector components
        self.vector_documents: List[str] = []
        self.vector_embeddings: Optional[np.ndarray] = None
        self.vector_metadata: List[Dict] = []
        
        # Graph channel
        self.graph_channel: Optional[GraphSearchChannel] = None
        
        # Cache
        self.cache = EmbeddingCache()
        
        # Initialize all channels
        self._load_documents()
        self._build_bm25_index()
        self._load_embeddings_parallel()
        self._init_graph_channel()
    
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
        
        print(f"Loaded {len(self.bm25_documents)} documents")
    
    def _build_bm25_index(self):
        if self.bm25_tokenized:
            self.bm25_index = BM25Okapi(self.bm25_tokenized)
            print(f"Built BM25 index with {len(self.bm25_tokenized)} documents")
    
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
    
    def _load_embeddings_parallel(self):
        embeddings = [None] * len(self.vector_documents)
        uncached_indices = [
            i for i, m in enumerate(self.vector_metadata)
            if not self.cache.get(m['full_path'], m['hash'])
        ]
        
        print(f"Computing embeddings for {len(uncached_indices)} uncached documents...")
        
        def fetch_embedding(idx):
            m = self.vector_metadata[idx]
            emb = self._get_embedding(
                self.vector_documents[idx],
                m['full_path'],
                m['hash']
            )
            return idx, emb
        
        if uncached_indices:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(fetch_embedding, idx): idx
                    for idx in uncached_indices
                }
                
                completed = 0
                for future in as_completed(futures):
                    idx, emb = future.result()
                    if emb is not None:
                        embeddings[idx] = emb
                    completed += 1
                    if completed % 20 == 0:
                        print(f"  Progress: {completed}/{len(uncached_indices)}")
        
        # Fill cached
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
            print(f"Loaded {len(valid_embeddings)} embeddings, shape: {self.vector_embeddings.shape}")
    
    def _init_graph_channel(self):
        """Initialize the graph search channel"""
        self.graph_channel = GraphSearchChannel(str(self.wiki_path))
        print(f"Graph channel initialized: {self.graph_channel.get_stats()}")
    
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
        """Vector similarity search"""
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
        """Triple RRF Fusion: BM25 + Vector + Graph"""
        scores = defaultdict(float)
        
        # BM25 contributions (weight: 1.0)
        for rank, (doc_idx, score) in enumerate(bm25_results):
            scores[doc_idx] += 1.0 / (k + rank + 1)
        
        # Vector contributions (weight: 1.0)
        for rank, (doc_idx, score) in enumerate(vector_results):
            scores[doc_idx] += 1.0 / (k + rank + 1)
        
        # Graph contributions (weight: 1.5 - higher because graph finds related docs)
        for rank, (doc_idx, score) in enumerate(graph_results):
            scores[doc_idx] += 1.5 / (k + rank + 1)
        
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        return [(doc_idx, score) for doc_idx, score in sorted_results]
    
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
        
        # Triple RRF fusion
        fused_results = self.rrf_fusion(bm25_results, vector_results, graph_results, self.rrf_k)
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
            
            response.append({
                'title': metadata['title'],
                'path': metadata['path'],
                'rrf_score': rrf_score,
                'bm25_score': bm25_score,
                'vector_score': vector_score,
                'graph_score': graph_score,
                'sources': sources,
                'expansion': self.expander.expand_query(query)[1][:3],
            })
        
        return response
    
    def _get_sources(self, bm25_score: float, vector_score: float, graph_score: float) -> List[str]:
        sources = []
        if bm25_score > 0:
            sources.append('bm25')
        if vector_score > 0.1:
            sources.append('vector')
        if graph_score > 0:
            sources.append('graph')
        return sources if sources else ['none']
    
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
    
    wiki_path = "/home/jacky/.openclaw/workspace/wiki"
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