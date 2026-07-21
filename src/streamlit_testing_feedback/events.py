import time
from contextlib import contextmanager

STARTED_SERVER_KEY = "stf:recording_started_server_ms"
EVENTS_KEY = "stf:events"


def _session_state():
    import streamlit as st

    return st.session_state


def is_recording() -> bool:
    """True while a feedback recording is in progress in this session."""
    return STARTED_SERVER_KEY in _session_state()


def log_event(type: str, **payload) -> None:
    """Record a tier-2 event; no-op unless a recording is in progress.

    Timestamps are ms offsets from recording start (clock-offset corrected),
    so events align with the video timeline.
    """
    state = _session_state()
    started = state.get(STARTED_SERVER_KEY)
    if started is None:
        return
    state.setdefault(EVENTS_KEY, []).append(
        {
            "type": type,
            "t_ms": round(time.time() * 1000 - started),
            "payload": payload,
        }
    )


@contextmanager
def instrument(name: str, **payload):
    """Time a block and log it as an event; records ok=False if it raised."""
    start = time.perf_counter()
    try:
        yield
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000)
        log_event(name, duration_ms=duration_ms, ok=False, **payload)
        raise
    duration_ms = round((time.perf_counter() - start) * 1000)
    log_event(name, duration_ms=duration_ms, ok=True, **payload)
