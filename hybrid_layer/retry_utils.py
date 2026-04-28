"""
Retry Utilities
OCM Sup v3 - Hybrid

簡單的 retry 工具，帶 exponential backoff。

Usage:
    from hybrid_layer.retry_utils import retry

    result = retry(
        lambda: api_call(),
        retries=3,
        delay=0.2,
        exponential=True
    )
"""

import time
import random
from typing import Callable, Any, Optional


def retry(
    fn: Callable,
    retries: int = 3,
    delay: float = 0.2,
    exponential: bool = True,
    jitter: bool = True,
    on_exception: Optional[Callable] = None
) -> Any:
    """
    Retry function with exponential backoff.
    
    Args:
        fn: Function to retry (no arguments)
        retries: Number of retry attempts
        delay: Base delay between retries (seconds)
        exponential: Multiply delay by 2^attempt
        jitter: Add random variation to delay (0.5-1.5x)
        on_exception: Optional callback when exception occurs
        
    Returns:
        Return value of fn
        
    Raises:
        Last exception if all retries fail
        
    Example:
        result = retry(lambda: fetch_url(url), retries=5)
    """
    last_exception = None
    
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            last_exception = e
            
            if on_exception:
                on_exception(e, attempt)
            
            if attempt < retries - 1:  # Not the last attempt
                # Calculate delay
                wait_time = delay
                
                if exponential:
                    wait_time = delay * (2 ** attempt)
                
                if jitter:
                    wait_time = wait_time * (0.5 + random.random())
                
                time.sleep(wait_time)
    
    # All retries failed
    raise last_exception


def retry_with_fallback(
    fn: Callable,
    fallback: Any,
    retries: int = 3,
    delay: float = 0.1
) -> Any:
    """
    Retry function, return fallback if all fail.
    
    Args:
        fn: Function to retry
        fallback: Value to return if all retries fail
        retries: Number of attempts
        delay: Delay between attempts
        
    Returns:
        fn() result, or fallback if all fail
    """
    try:
        return retry(fn, retries=retries, delay=delay)
    except Exception:
        return fallback
