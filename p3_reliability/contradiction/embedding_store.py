"""
Embedding Store - manages fact embeddings for contradiction detection.
Stores embeddings as numpy files with metadata index.
"""

import os
import json
import numpy as np
from typing import Optional
from datetime import datetime

EMBEDDING_DIR = os.path.expanduser("~/.openclaw/ocm-sup/embeddings/contradiction/")
os.makedirs(EMBEDDING_DIR, exist_ok=True)


class EmbeddingStore:
    """Stores and retrieves fact embeddings for similarity comparison."""

    def __init__(self):
        self._index_file = os.path.join(EMBEDDING_DIR, "index.json")
        self._index = self._load_index()
        self._embedding_dim = 1536  # nomic-embed-text dimension

    def _load_index(self) -> dict:
        """Load metadata index."""
        if os.path.exists(self._index_file):
            with open(self._index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"facts": {}, "last_updated": None}

    def _save_index(self):
        """Save metadata index."""
        self._index["last_updated"] = datetime.now().isoformat()
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    def store(self, fact_id: str, embedding: list[float], metadata: dict = None):
        """Store embedding for a fact."""
        # Save embedding as .npy
        emb_path = os.path.join(EMBEDDING_DIR, f"{fact_id}.npy")
        np.save(emb_path, np.array(embedding, dtype=np.float32))

        # Update index
        self._index["facts"][fact_id] = {
            "embedding_file": f"{fact_id}.npy",
            "stored_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self._save_index()

    def get(self, fact_id: str) -> Optional[np.ndarray]:
        """Retrieve embedding for a fact."""
        if fact_id not in self._index["facts"]:
            return None
        emb_path = os.path.join(EMBEDDING_DIR, f"{fact_id}.npy")
        if not os.path.exists(emb_path):
            return None
        return np.load(emb_path)

    def get_all(self) -> list[tuple[str, np.ndarray]]:
        """Get all stored embeddings as (fact_id, embedding) pairs."""
        results = []
        for fact_id in self._index["facts"]:
            emb = self.get(fact_id)
            if emb is not None:
                results.append((fact_id, emb))
        return results

    def delete(self, fact_id: str) -> bool:
        """Delete embedding for a fact."""
        if fact_id not in self._index["facts"]:
            return False
        emb_path = os.path.join(EMBEDDING_DIR, f"{fact_id}.npy")
        if os.path.exists(emb_path):
            os.remove(emb_path)
        del self._index["facts"][fact_id]
        self._save_index()
        return True

    def exists(self, fact_id: str) -> bool:
        """Check if embedding exists."""
        return fact_id in self._index["facts"]

    def count(self) -> int:
        """Return total stored embeddings."""
        return len(self._index["facts"])