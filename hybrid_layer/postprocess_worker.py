"""
Post-process Worker
OCM Sup v3 - Hybrid

Async post-processing: contradiction check, pruning, metrics
Runs in background to avoid blocking main write path.

Usage:
    from hybrid_layer.postprocess_worker import run_postprocess_async

    # After memory write is committed
    run_postprocess_async()
"""

import threading
from typing import Optional

# v3: Import retry utilities
from hybrid_layer.retry_utils import retry


def _run_contradiction_check():
    """
    Run contradiction check on all memories.
    Uses memory_reliability_layer.contradiction.
    """
    try:
        from memory_reliability_layer import ContradictionEngine
        engine = ContradictionEngine()
        results = engine.run_full_scan()
        return results
    except Exception as e:
        print(f"[POSTPROCESS] Contradiction check failed: {e}")
        return []


def _run_pruning():
    """
    Run adaptive pruning on memory.
    Uses memory_reliability_layer.adaptive_pruning.
    """
    try:
        from memory_reliability_layer import AdaptivePruning
        pruner = AdaptivePruning(threshold=0.7)
        
        # Load facts and usage data
        from memory_reliability_layer import config
        import json
        from pathlib import Path
        
        facts = []
        if config.STORAGE_DIR.exists():
            for fpath in config.STORAGE_DIR.glob("*.json"):
                try:
                    with open(fpath) as f:
                        data = json.load(f)
                        facts.append(data)
                except:
                    pass
        
        # Get usage data
        from memory_reliability_layer import UsageTracker
        tracker = UsageTracker()
        usage_data = {k: {"count": v.get("retrieve_count", 0)} 
                      for k, v in tracker._data.items()}
        
        result = pruner.execute(facts, usage_data, dry_run=True, max_prune=50)
        return result
    except Exception as e:
        print(f"[POSTPROCESS] Pruning failed: {e}")
        return None


def _run_health_metrics():
    """
    Compute and save health metrics.
    Uses memory_reliability_layer.health_metrics.
    """
    try:
        from memory_reliability_layer import HealthMetrics, UsageTracker, ContradictionEngine
        from memory_reliability_layer import config
        
        tracker = UsageTracker()
        contradiction_engine = ContradictionEngine()
        
        metrics = HealthMetrics(
            usage_tracker=tracker,
            contradiction_engine=contradiction_engine
        )
        report = metrics.compute()
        metrics.save_report(report)
        
        return report
    except Exception as e:
        print(f"[POSTPROCESS] Health metrics failed: {e}")
        return None


def run_postprocess_async(
    contradiction: bool = True,
    pruning: bool = True,
    metrics: bool = True
) -> None:
    """
    Run post-processing tasks in background threads.
    
    Args:
        contradiction: Run contradiction check
        pruning: Run adaptive pruning
        metrics: Run health metrics computation
    """
    if contradiction:
        def safe_contradiction():
            retry(_run_contradiction_check, retries=2)
        t = threading.Thread(target=safe_contradiction, daemon=True)
        t.start()
    
    if pruning:
        def safe_pruning():
            retry(_run_pruning, retries=2)
        t = threading.Thread(target=safe_pruning, daemon=True)
        t.start()
    
    if metrics:
        def safe_metrics():
            retry(_run_health_metrics, retries=2)
        t = threading.Thread(target=safe_metrics, daemon=True)
        t.start()


def run_postprocess_sync(
    contradiction: bool = True,
    pruning: bool = True,
    metrics: bool = True
) -> dict:
    """
    Run post-processing tasks synchronously (for testing).
    
    Returns:
        dict with results from each task
    """
    results = {}
    
    if contradiction:
        results["contradiction"] = _run_contradiction_check()
    
    if pruning:
        results["pruning"] = _run_pruning()
    
    if metrics:
        results["metrics"] = _run_health_metrics()
    
    return results
