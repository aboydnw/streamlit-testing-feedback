import base64
import time
from pathlib import Path
from typing import MutableMapping

from streamlit_testing_feedback import session

_STARTED_KEY = "stf_started_at"
_OFFSET_KEY = "stf_clock_offset_ms"
_WRITTEN_KEY = "stf_written_for"
_LAST_ZIP_KEY = "stf_last_zip"


def handle_value(
    value: dict | None, feedback_dir: Path, state: MutableMapping
) -> Path | None:
    """Process a component value idempotently across Streamlit reruns.

    Returns the written zip path on (and after) the stop payload, else None.
    """
    if not value:
        return None
    if value["status"] == "recording":
        if state.get(_STARTED_KEY) != value["startedAt"]:
            state[_STARTED_KEY] = value["startedAt"]
            state[_OFFSET_KEY] = time.time() * 1000 - value["startedAt"]
        return None
    if value["status"] == "stopped":
        if state.get(_WRITTEN_KEY) == value["startedAt"]:
            return state.get(_LAST_ZIP_KEY)
        meta = session.build_session_meta(
            app_url=value.get("app_url", ""),
            started_at_ms=value["startedAt"],
            duration_ms=value["duration_ms"],
            clock_offset_ms=state.get(_OFFSET_KEY, 0),
        )
        voice_b64 = value.get("voice_b64")
        path = session.write_session_zip(
            Path(feedback_dir),
            recording=base64.b64decode(value["recording_b64"]),
            voice=base64.b64decode(voice_b64) if voice_b64 else None,
            session=meta,
        )
        state[_WRITTEN_KEY] = value["startedAt"]
        state[_LAST_ZIP_KEY] = path
        return path
    return None


def feedback_recorder(dir: str = ".feedback", key: str = "stf_recorder"):
    """Mount the recorder component and write session zips into `dir`."""
    import streamlit as st
    import streamlit.components.v1 as components

    dist = Path(__file__).parent / "frontend" / "dist"
    recorder = components.declare_component(
        "streamlit_testing_feedback", path=str(dist)
    )
    value = recorder(key=key, default=None)
    return handle_value(value, Path(dir), st.session_state)
