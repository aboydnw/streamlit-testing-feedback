import datetime
import hashlib
import json
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from streamlit_testing_feedback import __version__

SCHEMA_VERSION = 1


def build_session_meta(
    *,
    app_url: str,
    started_at_ms: float,
    duration_ms: float,
    clock_offset_ms: float,
) -> dict:
    """Build the session.json payload.

    duration_ms is mandatory because MediaRecorder webm files carry no
    duration metadata; analysis tooling uses it to detect a truncated video.
    """
    started = datetime.datetime.fromtimestamp(started_at_ms / 1000, tz=datetime.UTC)
    return {
        "recorder": "streamlit-testing-feedback",
        "recorder_version": __version__,
        "schema_version": SCHEMA_VERSION,
        "app_url": app_url,
        "page": urlparse(app_url).path or "/",
        "started_at": started.isoformat(),
        "duration_ms": duration_ms,
        "clock_offset_ms": round(clock_offset_ms),
    }


def write_session_zip(
    feedback_dir: Path,
    *,
    recording: bytes,
    voice: bytes | None,
    session: dict,
    events: list | tuple = (),
) -> Path:
    """Assemble a riffrec-layout session zip and write it into feedback_dir."""
    feedback_dir = Path(feedback_dir)
    feedback_dir.mkdir(parents=True, exist_ok=True)
    path = feedback_dir / _zip_name(session)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("session.json", json.dumps(session, indent=2), zipfile.ZIP_DEFLATED)
        zf.writestr(
            "events.json",
            json.dumps(
                {"schema_version": SCHEMA_VERSION, "events": list(events)}, indent=2
            ),
            zipfile.ZIP_DEFLATED,
        )
        zf.writestr("recording.webm", recording, zipfile.ZIP_STORED)
        if voice is not None:
            zf.writestr("voice.webm", voice, zipfile.ZIP_STORED)
    return path


def _zip_name(session: dict) -> str:
    started = datetime.datetime.fromisoformat(session["started_at"])
    stamp = started.strftime("%Y-%m-%d-%H%M")
    short_id = hashlib.sha1(session["started_at"].encode()).hexdigest()[:6]
    return f"stf-{stamp}-{short_id}.zip"
