#!/usr/bin/env python3
"""
Unit Tests for Query Expansion Module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest
from query_expansion import QueryExpander


class TestQueryExpanderBasics:
    """Basic QueryExpander tests"""
    
    def setup_method(self):
        self.expander = QueryExpander()
    
    def test_expand_single_term_hermes(self):
        """Test expanding 'hermes' includes Chinese variants"""
        result = self.expander.expand_single_term("hermes")
        assert isinstance(result, set)
        assert len(result) > 1
        # Should include Chinese variants like 即夢
        assert any('\u4e00' <= c for c in str(result)), "Should include Chinese characters"
    
    def test_expand_single_term_chinese(self):
        """Test expanding Chinese term includes English variants"""
        result = self.expander.expand_single_term("期哥")
        assert isinstance(result, set)
        assert len(result) > 1
        english_chars = [c for c in str(result) if c.isascii()]
        assert len(english_chars) > 0, "Should include English characters"
    
    def test_expand_query_basic(self):
        """Test basic query expansion"""
        result = self.expander.expand_query("hermes")
        assert isinstance(result, tuple)
        assert len(result) == 2
        expanded_query, variants = result
        assert isinstance(expanded_query, str)
        assert isinstance(variants, list)
        assert len(variants) >= 1
        assert "hermes" in variants
    
    def test_expand_query_preserves_original(self):
        """Test that original query is always in variants"""
        queries = ["hermes", "期哥", "古洞站", "OpenClaw"]
        for q in queries:
            _, variants = self.expander.expand_query(q)
            assert q in variants, f"Original query '{q}' should be in variants"
    
    def test_expand_query_returns_tuple(self):
        """Test expand_query returns (expanded_query, variants)"""
        result = self.expander.expand_query("test")
        eq, vars = result
        assert isinstance(eq, str)
        assert isinstance(vars, list)
    
    def test_expand_query_empty_string(self):
        """Test empty query handling"""
        result = self.expander.expand_query("")
        assert result == ("", [])
    
    def test_expand_query_whitespace(self):
        """Test whitespace-only query"""
        result = self.expander.expand_query("   ")
        assert result[0] == "" or result[1] == []
    
    def test_is_chinese(self):
        """Test Chinese character detection"""
        assert self.expander.is_chinese("期哥") == True
        assert self.expander.is_chinese("hermes") == False
        assert self.expander.is_chinese("test123") == False
        assert self.expander.is_chinese("Hello世界") == True


class TestQueryExpanderEnglishChinese:
    """Test English-Chinese cross-lingual expansion"""
    
    def setup_method(self):
        self.expander = QueryExpander()
    
    def test_english_chinese_priority(self):
        """Test that English+Chinese variants are prioritized"""
        result = self.expander.expand_query("hermes")
        expanded_query, variants = result
        has_english = any(t.lower() in ['hermes', 'hermes agent'] for t in variants)
        has_chinese = any('\u4e00' <= c for c in ' '.join(variants))
        assert has_english, "Should have English variants"
        assert has_chinese, "Should have Chinese variants"
    
    def test_chinese_to_english(self):
        """Test Chinese query expands to English"""
        result = self.expander.expand_query("即夢")
        expanded_query, variants = result
        # Should have Hermes-related terms in variants
        has_hermes = False
        for v in variants:
            if 'hermes' in v.lower() or 'Hermes' in v:
                has_hermes = True
                break
        assert has_hermes, f"即夢 should expand to include Hermes variants, got: {variants}"
    
    def test_jacky_expansion(self):
        """Test 期哥 expands correctly"""
        result = self.expander.expand_query("期哥")
        _, variants = result
        assert any(v in ['Jacky', '積奇', '期哥'] for v in variants), \
            "期哥 should expand to Jacky/積奇"
    
    def test_astar_expansion(self):
        """Test 阿星 expands correctly"""
        result = self.expander.expand_query("阿星")
        _, variants = result
        # Should include Ah Sing, Star, 助手, etc.
        assert any(v in ['Ah Sing', 'Star', '助手', '阿星'] for v in variants), \
            "阿星 should expand to Ah Sing/Star"


class TestQueryExpanderPhrases:
    """Test phrase expansion"""
    
    def setup_method(self):
        self.expander = QueryExpander()
    
    def test_expand_phrase_bm25(self):
        """Test BM25 phrase expansion"""
        result = self.expander.expand_phrase("BM25")
        assert isinstance(result, list)
        assert "BM25" in result
    
    def test_expand_phrase_gutong(self):
        """Test 古洞站 phrase expansion"""
        result = self.expander.expand_phrase("古洞站")
        assert isinstance(result, list)
        # Should include Kwu Tung Station variant
        assert any('Kwu Tung' in v or 'gutong' in v.lower() for v in result), \
            "Should include Kwu Tung variant"


class TestQueryExpanderEntityExpansion:
    """Test entity-specific expansions"""
    
    def setup_method(self):
        self.expander = QueryExpander()
    
    def test_hermes_entity_expansion(self):
        """Test Hermes entity has multiple variants"""
        result = self.expander.expand_single_term("Hermes")
        assert len(result) >= 3, "Hermes should have at least 3 variants"
    
    def test_openclaw_expansion(self):
        """Test OpenClaw entity expansion"""
        result = self.expander.expand_query("OpenClaw")
        _, variants = result
        assert len(variants) >= 2, "OpenClaw should expand to multiple variants"
    
    def test_ocm_sup_expansion(self):
        """Test OCM Sup entity expansion"""
        result = self.expander.expand_query("OCM Sup")
        _, variants = result
        assert len(variants) >= 2, "OCM Sup should expand"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])