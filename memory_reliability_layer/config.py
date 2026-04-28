"""
Configuration for Memory Reliability Layer
OCM Sup v2.6
"""

from pathlib import Path

# Base directories
BASE_DIR = Path("~/.openclaw/ocm-sup").expanduser()
MEMORY_DIR = Path("~/.openclaw/workspace/memory").expanduser()

# Transaction manager
TX_DIR = BASE_DIR / "transactions"

# Storage layers
STORAGE_DIR = BASE_DIR / "structured"
VECTOR_DIR = BASE_DIR / "embeddings"
GRAPH_DIR = BASE_DIR / "graph"

# Archive
ARCHIVE_DIR = BASE_DIR / "archive"

# Usage tracking
USAGE_FILE = MEMORY_DIR / "usage_stats.json"

# Contradiction detection
CONTRADICTION_MODEL = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.75

# Pruning
PRUNE_THRESHOLD = 0.7
PRUNE_MAX_PER_RUN = 50
ARCHIVE_RETENTION_DAYS = 90
HALF_LIFE_DAYS = 30

# Health metrics
HEALTH_REPORT_DIR = BASE_DIR / "reports"
HEALTH_REPORT_PATH = HEALTH_REPORT_DIR / "weekly_report.json"

# Importance weights for pruning
IMPORTANCE_WEIGHTS = {
    "HIGH": 0.0,
    "MEDIUM": 0.3,
    "LOW": 0.6,
    "UNKNOWN": 0.5
}

# Default importance for facts without explicit importance
DEFAULT_IMPORTANCE = 0.5

# Ensure directories exist
for d in [TX_DIR, STORAGE_DIR, VECTOR_DIR, GRAPH_DIR, ARCHIVE_DIR, HEALTH_REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
