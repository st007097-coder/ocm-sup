"""
Idempotency Guard
OCM Sup v3.5 - Hybrid

防止同一 memory 重複寫入。
Based on content hash - same text = same memory.

Usage:
    from hybrid_layer.idempotency_guard import is_duplicate, make_id

    if is_duplicate(memory):
        return {"status": "duplicate"}
"""

import hashlib
import os
import json
import threading
from pathlib import Path

# Storage path
MEMORY_DIR = Path("~/.openclaw/workspace/memory").expanduser()
IDEMPOTENCY_FILE = MEMORY_DIR / "idempotency_keys.json"

# Ensure directory exists
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Thread-safe access
_lock = threading.Lock()


def _load() -> set:
    """Load idempotency keys from disk."""
    if not IDEMPOTENCY_FILE.exists():
        return set()
    try:
        with open(IDEMPOTENCY_FILE) as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()


def _save(keys: set):
    """Save idempotency keys to disk."""
    try:
        with open(IDEMPOTENCY_FILE, "w") as f:
            json.dump(list(keys), f, ensure_ascii=False)
    except IOError as e:
        print(f"[IDEMPOTENCY] Failed to save: {e}")


def make_id(memory: dict) -> str:
    """
    Generate deterministic ID from memory content.
    
    Args:
        memory: dict with 'subject' and 'action' keys
        
    Returns:
        SHA256 hash (first 16 chars)
    """
    # Combine subject and action for hashing
    subject = memory.get("subject", "").strip().lower()
    action = memory.get("action", "").strip().lower()
    content = f"{subject}:{action}"
    
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def is_duplicate(memory: dict) -> bool:
    """
    Check if memory is duplicate and mark as seen.
    
    Thread-safe.
    
    Args:
        memory: dict with 'subject' and 'action' keys
        
    Returns:
        True if duplicate (already seen), False if new
    """
    mid = make_id(memory)
    
    with _lock:
        seen = _load()
        
        if mid in seen:
            return True
        
        seen.add(mid)
        _save(seen)
        return False


def check_only(memory: dict) -> bool:
    """
    Check if memory is duplicate WITHOUT marking as seen.
    (For read-only queries)
    
    Returns:
        True if duplicate, False if new
    """
    mid = make_id(memory)
    
    with _lock:
        seen = _load()
        return mid in seen


def clear():
    """Clear all idempotency keys (for testing)."""
    with _lock:
        if IDEMPOTENCY_FILE.exists():
            IDEMPOTENCY_FILE.unlink()
        return True


def count() -> int:
    """Count how many keys are stored."""
    with _lock:
        return len(_load())
