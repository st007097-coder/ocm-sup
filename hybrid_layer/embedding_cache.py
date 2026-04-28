"""
Embedding Cache
OCM Sup v3 - Hybrid

Cache embeddings to avoid re-embedding identical texts.
大幅減少 API call 成本和 latency。

Usage:
    from hybrid_layer.embedding_cache import get, set

    # Check cache
    vector = get("same text to embed")
    if vector is None:
        vector = actual_embed("same text to embed")
        set("same text to embed", vector)
"""

import hashlib
import json
import threading
import os
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
CACHE_FILE = Path("~/.openclaw/ocm-sup/embeddings/cache.json")
MAX_CACHE_SIZE = 10000  # Max entries before LRU eviction

# Thread-safe access
_lock = threading.Lock()

# In-memory hot cache (LRU approximation)
_hot_cache: Dict[str, List[float]] = {}


def _normalize(text: str) -> str:
    """Normalize text for consistent hashing."""
    return text.strip().lower()


def _make_key(text: str) -> str:
    """Generate cache key from text."""
    norm = _normalize(text)
    return hashlib.sha256(norm.encode()).hexdigest()


def _load() -> Dict[str, List[float]]:
    """Load cache from disk."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save(cache: Dict[str, List[float]]):
    """Save cache to disk."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except IOError as e:
        print(f"[EMBED_CACHE] Failed to save: {e}")


def get(text: str) -> Optional[List[float]]:
    """
    Get cached embedding for text.
    
    Thread-safe.
    
    Args:
        text: Text to look up
        
    Returns:
        Cached vector if found, None if miss
    """
    key = _make_key(text)
    
    # Check hot cache first (fastest)
    with _lock:
        if key in _hot_cache:
            return _hot_cache[key]
    
    # Check disk cache
    with _lock:
        cache = _load()
        if key in cache:
            vector = cache[key]
            # Promote to hot cache
            _hot_cache[key] = vector
            return vector
    
    return None


def set(text: str, vector: List[float]):
    """
    Cache embedding for text.
    
    Thread-safe. Automatically handles eviction.
    
    Args:
        text: Text that was embedded
        vector: The embedding vector
    """
    key = _make_key(text)
    
    with _lock:
        # Update hot cache
        _hot_cache[key] = vector
        
        # Update disk cache with LRU eviction
        cache = _load()
        
        # Simple LRU: if over limit, remove oldest entries
        # (In production, use proper LRU library)
        if len(cache) >= MAX_CACHE_SIZE:
            # Remove ~10% of entries (simple eviction)
            keys_to_remove = list(cache.keys())[:MAX_CACHE_SIZE // 10]
            for k in keys_to_remove:
                del cache[k]
        
        cache[key] = vector
        _save(cache)


def has(text: str) -> bool:
    """Check if text is cached (without retrieving)."""
    key = _make_key(text)
    
    with _lock:
        if key in _hot_cache:
            return True
    
    with _lock:
        cache = _load()
        return key in cache


def clear():
    """Clear all cached embeddings."""
    global _hot_cache
    
    with _lock:
        _hot_cache = {}
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()


def count() -> int:
    """Count cached embeddings."""
    with _lock:
        disk_count = len(_load())
        hot_count = len(_hot_cache)
        return disk_count


def get_stats() -> dict:
    """Get cache statistics."""
    with _lock:
        disk_count = len(_load())
        hot_count = len(_hot_cache)
    
    return {
        "disk_entries": disk_count,
        "hot_cache_entries": hot_count,
        "max_size": MAX_CACHE_SIZE
    }
