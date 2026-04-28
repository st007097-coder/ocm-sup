"""
Vector Batcher
OCM Sup v3 - Hybrid

Batch embeddings for reduced latency and cost.
Buffers memories and flushes in batches.
Uses embedding cache to avoid re-embedding identical texts.

Usage:
    from hybrid_layer.vector_batcher import add_to_batch, start_background_worker

    # At startup
    start_background_worker()
    
    # In write path
    add_to_batch(memory)
"""

import threading
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from collections import deque

# Configuration
BATCH_SIZE = 8  # Number of items per batch
FLUSH_INTERVAL = 1.0  # Max seconds to wait before flushing
VECTOR_STORE_DIR = Path("~/.openclaw/ocm-sup/embeddings").expanduser()

# Ensure directory exists
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

# Buffer for pending items
_buffer: deque = deque()
_lock = threading.Lock()
_flush_lock = threading.Lock()

# Background worker
_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# v3: Embedding cache integration
try:
    from hybrid_layer.embedding_cache import get as cache_get, set as cache_set
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False


def _default_embed(texts: List[str]) -> List[List[float]]:
    """
    Default embedding function (placeholder).
    Replace with actual embedding model.
    
    Returns random vectors for testing.
    """
    import hashlib
    vectors = []
    for text in texts:
        # Simple hash-based pseudo-embedding
        h = hashlib.sha256(text.encode()).digest()
        vec = [float(b) / 255.0 for b in h[:8]]
        vectors.append(vec)
    return vectors


def _write_vector_store(memory_id: str, text: str, vector: List[float]):
    """Write single vector to storage."""
    filepath = VECTOR_STORE_DIR / f"{memory_id}.json"
    record = {
        "entity_id": memory_id,
        "text": text,
        "vector": vector,
        "timestamp": time.time()
    }
    with open(filepath, "w") as f:
        json.dump(record, f, ensure_ascii=False)


def _flush_batch():
    """Flush buffer to vector store."""
    global _buffer
    
    with _flush_lock:
        if not _buffer:
            return
        
        # Get batch
        batch = list(_buffer)
        _buffer.clear()
    
    if not batch:
        return
    
    # Extract texts
    texts = [item["text"] for item in batch]
    
    # v3: Check cache first to avoid re-embedding
    if HAS_CACHE:
        cached_vectors = []
        to_embed = []
        to_embed_idx = []
        
        for i, text in enumerate(texts):
            cached = cache_get(text)
            if cached is not None:
                cached_vectors.append((i, cached))
            else:
                to_embed.append(text)
                to_embed_idx.append(i)
        
        # Embed only uncached texts
        new_vectors = []
        if to_embed:
            try:
                new_vectors = _default_embed(to_embed)
                # Save to cache
                for text, vec in zip(to_embed, new_vectors):
                    cache_set(text, vec)
            except Exception as e:
                print(f"[VECTOR_BATCHER] Embed failed: {e}")
                # On failure, re-add to buffer
                with _lock:
                    _buffer.extendleft(reversed(batch))
                return
        
        # Merge results
        final_vectors = [None] * len(texts)
        for i, vec in cached_vectors:
            final_vectors[i] = vec
        for i, vec in zip(to_embed_idx, new_vectors):
            final_vectors[i] = vec
        
        vectors = final_vectors
    else:
        # No cache available, embed all
        try:
            vectors = _default_embed(texts)
        except Exception as e:
            print(f"[VECTOR_BATCHER] Embed failed: {e}")
            with _lock:
                _buffer.extendleft(reversed(batch))
            return
    
    # Write to store
    for item, vector in zip(batch, vectors):
        try:
            _write_vector_store(
                item["entity_id"],
                item["text"],
                vector
            )
        except Exception as e:
            print(f"[VECTOR_BATCHER] Write failed for {item['entity_id']}: {e}")


def add_to_batch(entity_id: str, text: str) -> bool:
    """
    Add memory to batch buffer.
    
    Thread-safe. Automatically flushes when batch is full.
    
    Args:
        entity_id: Unique ID for this memory
        text: Text content to embed
        
    Returns:
        True if added, False if buffer full (shouldn't happen)
    """
    global _buffer
    
    item = {
        "entity_id": entity_id,
        "text": text,
        "timestamp": time.time()
    }
    
    with _lock:
        _buffer.append(item)
        should_flush = len(_buffer) >= BATCH_SIZE
    
    if should_flush:
        # Trigger background flush (don't wait)
        threading.Thread(target=_flush_batch, daemon=True).start()
    
    return True


def force_flush():
    """Manually flush all buffered items."""
    _flush_batch()


def get_buffer_size() -> int:
    """Get current buffer size."""
    with _lock:
        return len(_buffer)


def _background_worker():
    """Background worker that flushes periodically."""
    while not _stop_event.is_set():
        time.sleep(FLUSH_INTERVAL)
        _flush_batch()


def start_background_worker():
    """Start the background flusher thread."""
    global _worker_thread
    
    if _worker_thread is not None and _worker_thread.is_alive():
        return  # Already running
    
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_background_worker, daemon=True)
    _worker_thread.start()
    print("[VECTOR_BATCHER] Background worker started")


def stop_background_worker():
    """Stop the background worker and flush remaining items."""
    global _worker_thread
    
    _stop_event.set()
    
    if _worker_thread is not None:
        _worker_thread.join(timeout=5.0)
        _worker_thread = None
    
    # Final flush
    force_flush()
    print("[VECTOR_BATCHER] Background worker stopped")
