from __future__ import annotations

"""Lightweight logging decorator for chat brain components.

Logs function name, minimal args summary, duration, and errors.
Avoids dumping full payloads to keep logs concise and privacy-aware.
"""

from functools import wraps
from time import perf_counter
from typing import Any, Callable
import logging
import os
import json
from datetime import datetime


# Configure logger with both console and file output
logger = logging.getLogger("chat")
if not logger.handlers:
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("[%(levelname)s] %(asctime)s %(name)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler - create logs directory if it doesn't exist
    logs_dir = "/app/logs/chat"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"chat_debug_{timestamp}.log")
    
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Chat debug logging initialized. File: {log_file}")

logger.setLevel(logging.INFO)


def _safe_preview(value: Any, maxlen: int = 120) -> str:
    try:
        if isinstance(value, str):
            v = value.strip().replace("\n", " ")
            return (v[: maxlen - 3] + "...") if len(v) > maxlen else v
        if isinstance(value, dict):
            # Show keys only
            return "{" + ", ".join(list(value.keys())[:8]) + ("..." if len(value) > 8 else "") + "}"
        if isinstance(value, (list, tuple)):
            return f"list(len={len(value)})"
        return repr(value)[:maxlen]
    except Exception:
        return "<unrepr>"


def log_call(name: str | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        disp = name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                preview_args = ", ".join(_safe_preview(a) for a in args[:3])
                preview_kwargs = "{" + ", ".join(list(kwargs.keys())[:8]) + ("..." if len(kwargs) > 8 else "") + "}"
            except Exception:
                preview_args, preview_kwargs = "<args>", "<kwargs>"
            logger.info(f"▶ {disp} args=[{preview_args}] kwargs={preview_kwargs}")
            start = perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = int((perf_counter() - start) * 1000)
                logger.info(f"✔ {disp} done in {duration_ms}ms")
                return result
            except Exception as e:
                duration_ms = int((perf_counter() - start) * 1000)
                logger.exception(f"✘ {disp} failed in {duration_ms}ms: {e}")
                raise

        return wrapper

    return decorator


def log_data_flow(name: str | None = None, log_inputs: bool = True, log_outputs: bool = True) -> Callable:
    """Enhanced decorator that logs detailed input/output data for debugging."""
    def decorator(func: Callable) -> Callable:
        disp = name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log inputs
            if log_inputs:
                try:
                    inputs_data = {
                        "args": [_detailed_safe_repr(a) for a in args[:5]],
                        "kwargs": {k: _detailed_safe_repr(v) for k, v in list(kwargs.items())[:10]}
                    }
                    logger.info(f"🔍 {disp} INPUTS: {json.dumps(inputs_data, indent=2, default=str)}")
                except Exception as e:
                    logger.info(f"🔍 {disp} INPUTS: <error serializing: {e}>")
            
            start = perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = int((perf_counter() - start) * 1000)
                
                # Log outputs
                if log_outputs:
                    try:
                        output_data = _detailed_safe_repr(result)
                        logger.info(f"📤 {disp} OUTPUT: {json.dumps(output_data, indent=2, default=str)}")
                    except Exception as e:
                        logger.info(f"📤 {disp} OUTPUT: <error serializing: {e}>")
                
                logger.info(f"✔ {disp} completed in {duration_ms}ms")
                return result
                
            except Exception as e:
                duration_ms = int((perf_counter() - start) * 1000)
                logger.error(f"💥 {disp} FAILED in {duration_ms}ms: {str(e)}")
                logger.exception(f"💥 {disp} FULL ERROR:")
                raise

        return wrapper
    return decorator


def _detailed_safe_repr(value: Any, max_items: int = 10) -> Any:
    """Create detailed but safe representation for logging."""
    try:
        if isinstance(value, str):
            return value[:500] + ("..." if len(value) > 500 else "")
        elif isinstance(value, dict):
            limited = dict(list(value.items())[:max_items])
            if len(value) > max_items:
                limited["__truncated__"] = f"... {len(value) - max_items} more items"
            return {k: _detailed_safe_repr(v, max_items=3) for k, v in limited.items()}
        elif isinstance(value, (list, tuple)):
            limited = value[:max_items]
            result = [_detailed_safe_repr(item, max_items=3) for item in limited]
            if len(value) > max_items:
                result.append(f"__truncated__ ... {len(value) - max_items} more items")
            return result
        elif hasattr(value, "__dict__"):
            # For objects, show class name and key attributes
            return {
                "__class__": value.__class__.__name__,
                "__attrs__": {k: _detailed_safe_repr(v, max_items=3) 
                             for k, v in list(value.__dict__.items())[:5]}
            }
        else:
            return str(value)[:200]
    except Exception:
        return f"<repr_error: {type(value).__name__}>"


