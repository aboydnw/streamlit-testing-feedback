"""Tier-2 event buffer.

Event state is app-global by design: `log_event` is called from application
code that doesn't know which recorder instance is mounted. Tier 2 assumes a
single recorder per app (multiple `feedback_recorder` mounts share one event
stream).
"""

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
    """Time a block, logging a ``phase="start"`` event on entry and a
    ``phase="end"`` event on exit.

    The start event means an abandoned operation still leaves a trace: a tester
    who kicks off a long op and navigates away is the common case, not the
    exception. The exit event catches ``BaseException`` (not just ``Exception``)
    so Streamlit's ``RerunException``/``StopException`` — raised to tear down an
    in-progress script run, and both subclasses of ``BaseException`` — are
    recorded rather than slipping through silently. ``interrupted`` is True when
    the block was killed by such a control-flow exception rather than failing
    with an ordinary error.
    """
    log_event(name, **{**payload, "phase": "start"})
    start = time.perf_counter()
    try:
        yield
    except BaseException as exc:
        duration_ms = round((time.perf_counter() - start) * 1000)
        log_event(
            name,
            **{
                **payload,
                "phase": "end",
                "duration_ms": duration_ms,
                "ok": False,
                "interrupted": not isinstance(exc, Exception),
            },
        )
        raise
    duration_ms = round((time.perf_counter() - start) * 1000)
    log_event(
        name,
        **{
            **payload,
            "phase": "end",
            "duration_ms": duration_ms,
            "ok": True,
            "interrupted": False,
        },
    )
