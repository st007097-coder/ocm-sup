"""
Hybrid Layer - OCM Sup v3.5

選擇性非同步層 - 將慢操作解耦，保持同步主流程。

Phase 1: Reliability
    - async_runner: 簡單 background thread 執行
    - idempotency_guard: 防止重複寫入
    - retry_utils: Retry with backoff

Phase 2: Latency Optimization
    - vector_batcher: Batch embeddings (8條/批)
    - embedding_cache: Cache embeddings

Usage:
    from hybrid_layer import run_async, is_duplicate

    run_async(slow_function, arg)
    if is_duplicate(memory):
        return {"status": "duplicate"}
        
    from hybrid_layer.vector_batcher import add_to_batch, start_background_worker
    start_background_worker()
    add_to_batch(entity_id, text)
"""

from .async_runner import run_async, run_async_with_callback, run_delayed
from .idempotency_guard import is_duplicate, make_id, check_only, clear
from .retry_utils import retry, retry_with_fallback
from .vector_batcher import add_to_batch, start_background_worker, stop_background_worker, get_buffer_size, force_flush
from .embedding_cache import get, set, has, clear, count, get_stats

__all__ = [
    # Async runner
    "run_async",
    "run_async_with_callback",
    "run_delayed",
    # Idempotency
    "is_duplicate",
    "make_id",
    "check_only",
    "clear",
    # Retry
    "retry",
    "retry_with_fallback",
    # Vector batcher
    "add_to_batch",
    "start_background_worker",
    "stop_background_worker",
    "get_buffer_size",
    "force_flush",
    # Embedding cache
    "get",
    "set",
    "has",
    "clear",
    "count",
    "get_stats",
]
