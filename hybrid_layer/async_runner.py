"""
Async Runner
OCM Sup v3.5 - Hybrid

最簡單的 background task 執行器。
使用 threading 而非 asyncio - 低侵入、立即可用。

Usage:
    from hybrid_layer.async_runner import run_async

    run_async(my_function, arg1, arg2, kwarg1=value)
"""

import threading
from typing import Callable, Any, Optional
from functools import wraps


def run_async(fn: Callable, *args, **kwargs) -> None:
    """
    Run function in background thread (fire-and-forget).
    
    Args:
        fn: Function to run
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Example:
        run_async(write_to_disk, data, filename="output.txt")
        run_async(send_email, to="user@example.com")
    """
    t = threading.Thread(
        target=_run_wrapper,
        args=(fn, args, kwargs),
        daemon=True
    )
    t.start()


def _run_wrapper(fn: Callable, args: tuple, kwargs: dict):
    """Wrapper to catch exceptions in background thread."""
    try:
        fn(*args, **kwargs)
    except Exception as e:
        print(f"[ASYNC] Error in background task {fn.__name__}: {e}")


def run_async_with_callback(
    fn: Callable,
    callback: Callable,
    *args,
    **kwargs
) -> None:
    """
    Run function in background and call callback when done.
    
    Args:
        fn: Function to run
        callback: Function to call when fn completes
        *args, **kwargs: Arguments for fn
    """
    def _with_callback():
        try:
            result = fn(*args, **kwargs)
            if callback:
                callback(result)
        except Exception as e:
            print(f"[ASYNC] Error in {fn.__name__}: {e}")
            if callback:
                callback(None)
    
    t = threading.Thread(target=_with_callback, daemon=True)
    t.start()


def run_delayed(delay: float, fn: Callable, *args, **kwargs) -> None:
    """
    Run function after delay (in seconds).
    
    Args:
        delay: Seconds to wait
        fn: Function to run
        *args, **kwargs: Arguments
        
    Example:
        run_delayed(5.0, cleanup_function)  # Run after 5 seconds
    """
    def _delayed():
        import time
        time.sleep(delay)
        try:
            fn(*args, **kwargs)
        except Exception as e:
            print(f"[ASYNC] Error in delayed task {fn.__name__}: {e}")
    
    t = threading.Thread(target=_delayed, daemon=True)
    t.start()
