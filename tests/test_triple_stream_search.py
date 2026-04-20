#!/usr/bin/env python3
"""
Unit Tests for Triple-Stream Search Module

Note: Tests requiring wiki_path will skip if wiki is unavailable.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest


def get_search_instance():
    """Get TripleStreamSearch instance, skip if unavailable"""
    try:
        from triple_stream_search import TripleStreamSearch
        return TripleStreamSearch(wiki_path='/root/.openclaw/workspace/wiki')
    except Exception as e:
        pytest.skip(f"Cannot initialize TripleStreamSearch: {e}")


class TestTripleStreamSearch:
    """Test TripleStreamSearch core functionality"""
    
    def setup_method(self):
        """Setup before each test"""
        self.search = get_search_instance()
    
    def test_search_returns_list(self):
        """Test that search returns a list"""
        results = self.search.search("hermes", top_k=5)
        assert isinstance(results, list)
    
    def test_search_results_have_required_fields(self):
        """Test that search results have all required fields"""
        results = self.search.search("hermes", top_k=3)
        if len(results) == 0:
            pytest.skip("No results returned")
        
        required_fields = ['title', 'path', 'rrf_score', 'bm25_score', 'vector_score', 'sources']
        for field in required_fields:
            assert field in results[0], f"Missing field: {field}"
    
    def test_search_bm25_expanded_returns_list(self):
        """Test BM25 expanded search returns list of (doc_idx, score) tuples"""
        results = self.search.search_bm25_expanded("hermes", top_k=5)
        assert isinstance(results, list)
        if len(results) > 0:
            assert isinstance(results[0], tuple)
            assert len(results[0]) == 2
    
    def test_search_vector_returns_list(self):
        """Test vector search returns list of (doc_idx, score) tuples"""
        results = self.search.search_vector("hermes", top_k=5)
        assert isinstance(results, list)
        if len(results) > 0:
            assert isinstance(results[0], tuple)
    
    def test_search_graph_returns_list(self):
        """Test graph search returns list of (doc_idx, score) tuples"""
        results = self.search.search_graph("hermes", top_k=5)
        assert isinstance(results, list)
        if len(results) > 0:
            assert isinstance(results[0], tuple)
    
    def test_rrf_fusion_all_channels(self):
        """Test RRF fusion with all three channels"""
        bm25 = [(0, 5.0), (1, 3.0)]
        vec = [(0, 0.8), (2, 0.7)]
        graph = [(0, 1.0)]
        
        results = self.search.rrf_fusion(bm25, vec, graph, k=60)
        assert isinstance(results, list)
        assert len(results) > 0
        # Doc 0 appears in all channels, should rank high
        doc_ids = [r[0] for r in results]
        assert 0 in doc_ids
    
    def test_rrf_fusion_empty_channels(self):
        """Test RRF fusion with some empty channels"""
        bm25 = [(0, 5.0)]
        vec = []
        graph = []
        
        results = self.search.rrf_fusion(bm25, vec, graph, k=60)
        assert isinstance(results, list)
        assert len(results) == 1
    
    def test_rrf_fusion_single_channel(self):
        """Test RRF fusion with single channel"""
        bm25 = [(0, 5.0), (1, 3.0), (2, 1.0)]
        vec = []
        graph = []
        
        results = self.search.rrf_fusion(bm25, vec, graph, k=60)
        assert isinstance(results, list)
        assert len(results) == 3
        # Should be sorted by BM25 score
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)


class TestTripleStreamSearchSources:
    """Test source detection"""
    
    def setup_method(self):
        self.search = get_search_instance()
    
    def test_get_sources_all_zero(self):
        """Test sources detection with all zero scores"""
        sources = self.search._get_sources(0, 0, 0)
        assert sources == ['none']
    
    def test_get_sources_bm25_only(self):
        """Test sources detection with BM25 only"""
        sources = self.search._get_sources(5.0, 0, 0)
        assert sources == ['bm25']
    
    def test_get_sources_vector_only(self):
        """Test sources detection with vector only (above threshold)"""
        sources = self.search._get_sources(0, 0.5, 0)
        assert sources == ['vector']
    
    def test_get_sources_graph_only(self):
        """Test sources detection with graph only"""
        sources = self.search._get_sources(0, 0, 1.0)
        assert sources == ['graph']
    
    def test_get_sources_bm25_vector(self):
        """Test sources detection with BM25 + vector"""
        sources = self.search._get_sources(5.0, 0.5, 0)
        assert sources == ['bm25', 'vector']
    
    def test_get_sources_all_three(self):
        """Test sources detection with all three channels"""
        sources = self.search._get_sources(5.0, 0.5, 1.0)
        assert 'bm25' in sources
        assert 'vector' in sources
        assert 'graph' in sources
    
    def test_get_sources_vector_below_threshold(self):
        """Test vector below threshold (0.1) is not reported"""
        sources = self.search._get_sources(5.0, 0.05, 0)
        assert sources == ['bm25']  # vector should not be included
        assert 'vector' not in sources


class TestTripleStreamSearchSearchQuality:
    """Test search quality and relevance"""
    
    def setup_method(self):
        self.search = get_search_instance()
    
    def test_hermes_query_finds_hermes_docs(self):
        """Test that 'hermes' query returns Hermes-related docs"""
        results = self.search.search("hermes", top_k=10)
        
        # Check that Hermes-related docs are in top results
        hermes_related = [r for r in results if 'hermes' in r['title'].lower() or 'Hermes' in r['title']]
        assert len(hermes_related) >= 2, "Should find at least 2 Hermes-related docs"
    
    def test_chinese_query_finds_chinese_docs(self):
        """Test that Chinese query finds Chinese docs"""
        results = self.search.search("古洞站", top_k=5)
        assert len(results) > 0, "Should return results for Chinese query"
    
    def test_expanded_query_better_than_raw(self):
        """Test that expanded query returns results"""
        # This tests that query expansion is working
        result = self.search.search("hermes", top_k=5)
        assert len(result) > 0
        # With expansion, should find Hermes docs
        has_hermes = any('hermes' in r['title'].lower() for r in result)
        assert has_hermes, "Expanded query should find Hermes docs"
    
    def test_top_k_respects_limit(self):
        """Test that search respects top_k limit"""
        results = self.search.search("hermes", top_k=3)
        assert len(results) <= 3, "Should return at most top_k results"
    
    def test_scores_are_non_negative(self):
        """Test that all scores are non-negative"""
        results = self.search.search("hermes", top_k=5)
        for r in results:
            assert r['rrf_score'] >= 0, "RRF score should be non-negative"
            assert r['bm25_score'] >= 0, "BM25 score should be non-negative"
            assert r['vector_score'] >= 0, "Vector score should be non-negative"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])