#!/usr/bin/env python3
"""
Query Expansion Module
- Chinese-English synonym expansion
- Domain-specific term expansion
- Automatic query rewriting
"""

import re
from typing import List, Set, Dict, Tuple, Optional


class QueryExpander:
    """
    Query expansion with synonyms and related terms
    """
    
    def __init__(self):
        # Chinese-English synonym dictionary
        self.synonyms: Dict[str, Set[str]] = {
            # AI / Tech terms
            "知識圖譜": {"knowledge graph", "knowledge-graph", "知識圖譜", "知識graph"},
            "知識圖": {"knowledge graph", "knowledge-graph", "知識圖譜"},
            "graph": {"graph", "圖譜", "關係圖", "知識圖"},
            "圖譜": {"graph", "知識圖譜", "knowledge graph"},
            "向量搜索": {"vector search", "vector similarity", "embedding search"},
            "向量": {"vector", "向量", "embedding", "embeddings"},
            "搜尋": {"search", "搜尋", "搜索", "检索", "retrieval"},
            "搜索": {"search", "搜尋", "检索", "retrieval"},
            
            # Memory systems
            "記憶系統": {"memory system", "persistent memory", "long-term memory", "記憶系統"},
            "記憶": {"memory", "記憶", "memories"},
            "上下文": {"context", "上下文", "context window"},
            "長期記憶": {"long-term memory", "persistent memory", "長期記憶"},
            "短期記憶": {"short-term memory", "working memory", "短期記憶"},
            
            # OCM Sup terms
            "記憶層次": {"memory tier", "memory hierarchy", "tiered memory", "層次"},
            "層次": {"tier", "level", "layer", "層次", "层级"},
            "蒸餾": {"distillation", "distill", "consolidation", "蒸餾", "提炼"},
            "記憶蒸餾": {"memory distillation", "memory distill", "記憶蒸餾", "知識蒸餾"},
            "整合": {"integration", "integrate", "合併", "整合"},
            "蒸發": {"eviction", "forgetting", "evict", "蒸發", "遺忘"},
            
            # Tech concepts
            "檢索": {"retrieval", "search", "搜索", "retrieval"},
            "相似度": {"similarity", "similar", "相似性", "相似"},
            "嵌入": {"embedding", "embed", "嵌入", "vector"},
            "向量化": {"vectorization", "embedding", "向量化"},
            "相似性搜索": {"similarity search", "semantic search", "相似性搜索"},
            "語義搜索": {"semantic search", "semantic retrieval", "語義搜索"},
            
            # AI Agent terms
            "AI助手": {"AI assistant", "assistant", "AI助手", "helper"},
            "助手": {"assistant", "helper", "幫手", "助手"},
            "智能體": {"agent", "AI agent", "智能體", "agent"},
            "代理": {"agent", "proxy", "代理", "agent"},
            "AI智能體": {"AI agent", "agent", "AI智能體", "智能體"},
            
            # File types
            "文檔": {"document", "doc", "文檔", "文档"},
            "文件": {"document", "docs", "文件", "文档"},
            "筆記": {"note", "notes", "筆記", "note"},
            
            # Quality terms
            "QS": {"quantity surveyor", "工料測量師", "QS"},
            "工料測量": {"quantity surveying", "工料測量", "QS"},
            "工料測量師": {"quantity surveyor", "工料測量師", "QS", "工料測量"},
            "估算": {"estimation", "估算", "estimate"},
            "造價": {"cost", "造價", "costing", "造價"},
            
            # Construction / QS terms
            "分判商": {"subcontractor", "分判商", "sub-contractor"},
            "供應商": {"supplier", "供應商", "vendor"},
            "投標": {"tendering", "投標", "bidding", "投標"},
            "合約": {"contract", "合約", "agreement"},
            "工程": {"engineering", "工程", "construction"},
            "工程合約": {"construction contract", "工程合約", "contract"},
            "造價估算": {"cost estimation", "造價估算", "estimation"},
            
            # Distillation terms
            "蒸餾": {"distillation", "蒸餾", "蒸餾"},
            "知識蒸餾": {"knowledge distillation", "知識蒸餾", "distillation"},
            
            # Person entities
            "期哥": {"Jacky", "期哥", "jacky", "積奇", "Jacky Evolution", "QS期哥"},
            "阿星": {"Ah Sing", "阿星", "Star", "ah sing", "assistant", "AI助手", "助手"},
            "Jacky": {"期哥", "Jacky", "jacky", "積奇"},
            "Star": {"阿星", "Ah Sing", "Star", "assistant", "AI助手"},
            
            # Project terms
            "古洞站": {"gutong station", "古洞站", "Kwu Tung Station", "Kwu Tung", "古洞"},
            "東鐵": {"East Rail", "east rail", "東鐵", "East Rail Line"},
            "東鐵線": {"East Rail Line", "east rail", "東鐵線", "East Rail"},
            "項目": {"project", "項目", "project"},
            "地盤": {"site", "construction site", "地盤", "工地"},
            
            # OCM Sup concepts
            "OCM Sup": {"OCM Sup", "OCM-Sup", "ocm-sup", "OpenClaw Memory Supervisor"},
            "EvoMap": {"EvoMap", "evomap", "Evo Map"},
            
            # System entities (agents, tools)
            "Hermes": {"Hermes", "hermes", "Hermes Agent", "hermes agent", "即夢", "即夢AI"},
            "Hermes Agent": {"Hermes", "hermes agent", "Hermes Agent", "即夢", "即夢AI"},
            "OpenClaw": {"OpenClaw", "openclaw", "Open Claw", "claw"},
            "Claude": {"Claude", "claude", "Anthropic Claude", "claude ai"},
            "即夢": {"即夢", "即夢AI", "Jiemeng", "Hermes", "hermes"},
            "Telegram": {"Telegram", "telegram", "TG"},
            
            # Dreaming/Consolidation
            "Dreaming": {"dreaming", "Dreaming", "睡眠整合", "dream consolidation"},
            "整合循環": {"consolidation loop", "consolidation", "整合循環"},
            "知識蒸餾": {"knowledge distillation", "distillation", "知識蒸餾"},
            
            # Wiki/Entities
            "Wiki": {"wiki", "Wiki", "知識庫", "knowledge base"},
            "實體": {"entity", "entities", "實體", "entity"},
            "實體關係": {"entity relationship", "relationships", "實體關係"},
            
            # Cron/Auto tasks
            "定時任務": {"cron job", "scheduled task", "定時任務", "cron"},
            "自動任務": {"automated task", "auto task", "自動任務"},
            
            # Notion
            "Notion": {"Notion", "notion", "笔记工具"},
            "VO Tracker": {"VO Tracker", "vo tracker", "VO追蹤"},
            
            # Obsidian
            "Obsidian": {"Obsidian", "obsidian", "筆記軟件"},
            "Vault": {"vault", "Obsidian vault", "知識庫"},
            
            # Search terms
            "關鍵詞搜索": {"keyword search", "exact match", "關鍵詞搜索"},
            "語義匹配": {"semantic match", "semantic similarity", "語義匹配"},
            "混合搜索": {"hybrid search", "mixed search", "混合搜索"},
            "混合檢索": {"hybrid retrieval", "hybrid search", "混合檢索"},
        }
        
        # Reverse mapping (English to Chinese)
        self.reverse_synonyms: Dict[str, Set[str]] = {}
        for cn_terms, en_terms in self.synonyms.items():
            for en in en_terms:
                if en not in self.reverse_synonyms:
                    self.reverse_synonyms[en] = set()
                self.reverse_synonyms[en].add(cn_terms)
        
        # Combine both directions
        self.all_synonyms: Dict[str, Set[str]] = {}
        for terms in list(self.synonyms.items()) + list(self.reverse_synonyms.items()):
            main_term = list(terms)[0] if isinstance(terms, set) else None
            if main_term:
                self.all_synonyms[main_term] = terms
        
        # Domain-specific expansions (multi-word phrases)
        self.phrase_expansions: Dict[str, List[str]] = {
            "BM25": ["BM25", "Okapi BM25", "BM25L", "BM25+"],
            "RRF": ["RRF", "Reciprocal Rank Fusion", "rank fusion"],
            "OCM Sup": ["OCM Sup", "OCM-Sup", "ocm-sup", "OpenClaw Memory Supervisor"],
            "OpenClaw": ["OpenClaw", "openclaw", "Open Claw"],
            "古洞站": ["古洞站", "Kwu Tung Station", "gutong station"],
            "知識圖譜": ["知識圖譜", "knowledge graph", "knowledge-graph"],
            "記憶蒸餾": ["memory distillation", "memory distill", "記憶蒸餾", "知識蒸餾"],
            "Quantity Surveyor": ["Quantity Surveyor", "quantity surveyor", "工料測量師"],
            "工料測量師": ["工料測量師", "Quantity Surveyor", "quantity surveyor"],
            "知識蒸餾": ["知識蒸餾", "knowledge distillation", "memory distillation"],
            "知識圖譜": ["知識圖譜", "knowledge graph", "knowledge-graph"],
        }
    
    def is_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def expand_single_term(self, term: str) -> Set[str]:
        """Expand a single term with synonyms"""
        term = term.strip().lower()
        expanded = {term}
        
        # Check if term has known synonyms
        if term in self.synonyms:
            expanded.update(self.synonyms[term])
        
        # Check reverse mapping
        if term in self.reverse_synonyms:
            expanded.update(self.reverse_synonyms[term])
        
        # If Chinese, also try English translation
        if self.is_chinese(term):
            for cn, en_set in self.synonyms.items():
                if term == cn.lower() or term in cn.lower():
                    expanded.update(en_set)
        else:
            # If English, try to find Chinese
            for cn, en_set in self.synonyms.items():
                if term in en_set:
                    expanded.add(cn)
                    expanded.update(en_set)
        
        # Remove the original if we added expansions
        if len(expanded) > 1:
            expanded.discard(term)
        
        return expanded
    
    def expand_phrase(self, phrase: str) -> List[str]:
        """Expand a multi-word phrase"""
        phrase_lower = phrase.lower().strip()
        
        # Check phrase expansions
        for key, expansions in self.phrase_expansions.items():
            if key.lower() in phrase_lower:
                # Replace key with each expansion variant
                results = []
                for exp in expansions:
                    new_phrase = re.sub(re.escape(key), exp, phrase, flags=re.IGNORECASE)
                    results.append(new_phrase)
                return results
        
        return [phrase]
    
    def expand_query(self, query: str, max_expansions: int = 10) -> Tuple[str, List[str]]:
        """
        Expand a query with synonyms
        
        Returns:
            Tuple of (expanded_query, list_of_expansion_variants)
        """
        query = query.strip()
        if not query:
            return "", []
        
        # First, check for phrase expansions
        phrase_variants = self.expand_phrase(query)
        
        # Tokenize
        tokens = re.split(r'[\s,，、]+', query)
        tokens = [t.strip() for t in tokens if t.strip()]
        
        if not tokens:
            return query, [query]
        
        # Expand each token
        all_expansions = []
        for token in tokens:
            expanded = self.expand_single_term(token)
            if expanded and len(expanded) > 1:
                all_expansions.append(expanded)
            else:
                all_expansions.append({token})
        
        # Generate combination expansions (limited)
        variants = []
        
        # Always include original
        variants.append(query)
        
        # Add phrase variants
        variants.extend(phrase_variants[:3])
        
        # Generate limited combinations
        if all_expansions and len(all_expansions) <= 4:
            for i, expansion_set in enumerate(all_expansions):
                if len(expansion_set) > 1:
                    # Prioritize: 1 English + 1 other (if available)
                    expansion_list = list(expansion_set)
                    english_variants = [v for v in expansion_list if v and v[0].isascii()]
                    other_variants = [v for v in expansion_list if v and not v[0].isascii()]
                    selected = []
                    if english_variants:
                        selected.append(english_variants[0])
                    if other_variants and len(selected) < 2:
                        selected.append(other_variants[0])
                    elif len(english_variants) > 1 and len(selected) < 2:
                        selected.append(english_variants[1])
                    for exp_term in selected:
                        new_query = tokens[:i] + [exp_term] + tokens[i+1:]
                        new_phrase = ' '.join(new_query)
                        if new_phrase not in variants:
                            variants.append(new_phrase)
        
        # Limit total variants
        variants = variants[:max_expansions]
        
        # Create expanded query (OR all terms)
        expanded_query = ' '.join(variants[:5])
        
        return expanded_query, variants
    
    def get_related_terms(self, term: str, max_terms: int = 5) -> List[str]:
        """Get related terms for a given term"""
        expanded = self.expand_single_term(term)
        # Remove original term
        expanded.discard(term.lower())
        expanded.discard(term)
        
        # Sort by length (prefer same-language matches)
        def sort_key(t):
            same_lang = 0 if (self.is_chinese(t) == self.is_chinese(term)) else 1
            return (same_lang, len(t))
        
        sorted_terms = sorted(expanded, key=sort_key)
        
        return sorted_terms[:max_terms]


def test_expander():
    """Test the query expander"""
    expander = QueryExpander()
    
    test_queries = [
        "知識圖譜",
        "知識圖",
        "BM25",
        "OCM Sup",
        "古洞站",
        "記憶系統層次",
        "AI助手",
        "向量搜索",
        "記憶蒸餾",
    ]
    
    print("🧪 Query Expansion Test")
    print("=" * 60)
    
    for query in test_queries:
        expanded, variants = expander.expand_query(query)
        related = expander.get_related_terms(query)
        
        print(f"\n📝 Query: {query}")
        print(f"   Expanded: {expanded}")
        print(f"   Variants: {variants}")
        print(f"   Related: {related}")
    
    print("\n✅ Test complete")


if __name__ == "__main__":
    test_expander()