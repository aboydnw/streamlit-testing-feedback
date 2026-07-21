import base64
import time
from pathlib import Path
from typing import MutableMapping

from streamlit_testing_feedback import session


def handle_value(
    value: dict | None,
    feedback_dir: Path,
    state: MutableMapping,
    *,
    key: str = "stf_recorder",
) -> Path | None:
    """Process a component value idempotently across Streamlit reruns.

    State entries are namespaced by `key` so multiple recorder instances
    don't clobber each other. Returns the written zip path on (and after)
    the stop payload, else None.
    """
    started_key = f"{key}:started_at"
    offset_key = f"{key}:clock_offset_ms"
    written_key = f"{key}:written_for"
    last_zip_key = f"{key}:last_zip"

    if not value:
        return None
    if value["status"] == "recording":
        if state.get(started_key) != value["startedAt"]:
            state[started_key] = value["startedAt"]
            state[offset_key] = time.time() * 1000 - value["startedAt"]
        return None
    if value["status"] == "stopped":
        if state.get(written_key) == value["startedAt"]:
            return state.get(last_zip_key)
        meta = session.build_session_meta(
            app_url=value.get("app_url", ""),
            started_at_ms=value["startedAt"],
            duration_ms=value["duration_ms"],
            clock_offset_ms=state.get(offset_key, 0),
        )
        voice_b64 = value.get("voice_b64")
        path = session.write_session_zip(
            Path(feedback_dir),
            recording=base64.b64decode(value["recording_b64"]),
            voice=base64.b64decode(voice_b64) if voice_b64 else None,
            session=meta,
        )
        state[written_key] = value["startedAt"]
        state[last_zip_key] = path
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
    return handle_value(value, Path(dir), st.session_state, key=key)
