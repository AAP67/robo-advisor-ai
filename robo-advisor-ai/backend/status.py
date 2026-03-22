"""
RoboAdvisor AI — Status Callback
Thread-safe status emission for streaming updates to the frontend.
Separate module to avoid circular imports between graph.py and agents.
"""

import threading
from typing import Callable, Optional


_thread_local = threading.local()


def set_status_callback(callback: Optional[Callable[[str], None]]):
    """Set a status callback for the current thread."""
    _thread_local.status_callback = callback


def get_status_callback() -> Optional[Callable[[str], None]]:
    """Get the status callback for the current thread."""
    return getattr(_thread_local, "status_callback", None)


def emit_status(message: str):
    """Emit a status update if a callback is registered."""
    cb = get_status_callback()
    if cb:
        cb(message)
    print(f"  📡 {message}")