import base64
import json
import zipfile

import pytest

from streamlit_testing_feedback import component, events

STARTED_MS = 1753100000000.0


def start_value():
    return {"status": "recording", "startedAt": STARTED_MS}


def stop_value():
    return {
        "status": "stopped",
        "startedAt": STARTED_MS,
        "duration_ms": 61250.0,
        "app_url": "http://localhost:8501/corpus",
        "recording_b64": base64.b64encode(b"WEBMDATA").decode(),
        "voice_b64": base64.b64encode(b"VOICEDATA").decode(),
    }


@pytest.fixture
def frozen_now(monkeypatch):
    monkeypatch.setattr(component.time, "time", lambda: STARTED_MS / 1000 + 0.150)


def test_none_value_is_noop(tmp_path):
    assert component.handle_value(None, tmp_path, {}) is None


def test_start_records_clock_offset(tmp_path, frozen_now):
    state = {}
    result = component.handle_value(start_value(), tmp_path, state)
    assert result is None
    assert state["stf_recorder:clock_offset_ms"] == pytest.approx(150.0)


def test_offset_not_recomputed_on_rerun(tmp_path, frozen_now, monkeypatch):
    state = {}
    component.handle_value(start_value(), tmp_path, state)
    monkeypatch.setattr(component.time, "time", lambda: STARTED_MS / 1000 + 99)
    component.handle_value(start_value(), tmp_path, state)
    assert state["stf_recorder:clock_offset_ms"] == pytest.approx(150.0)


def test_state_namespaced_by_key(tmp_path, frozen_now):
    state = {}
    component.handle_value(start_value(), tmp_path, state, key="a")
    assert "a:clock_offset_ms" in state
    assert "b:clock_offset_ms" not in state
    component.handle_value(stop_value(), tmp_path, state, key="a")
    path_b = component.handle_value(stop_value(), tmp_path, state, key="b")
    assert path_b is not None


def test_stop_writes_zip(tmp_path, frozen_now):
    state = {}
    component.handle_value(start_value(), tmp_path, state)
    path = component.handle_value(stop_value(), tmp_path, state)
    assert path is not None and path.exists()
    with zipfile.ZipFile(path) as zf:
        assert zf.read("recording.webm") == b"WEBMDATA"
        assert zf.read("voice.webm") == b"VOICEDATA"


def test_stop_rerun_does_not_double_write(tmp_path, frozen_now):
    state = {}
    component.handle_value(start_value(), tmp_path, state)
    first = component.handle_value(stop_value(), tmp_path, state)
    second = component.handle_value(stop_value(), tmp_path, state)
    assert first == second
    assert len(list(first.parent.glob("*.zip"))) == 1


def test_stop_without_start_still_writes(tmp_path, frozen_now):
    path = component.handle_value(stop_value(), tmp_path, {})
    assert path is not None and path.exists()


def test_start_initializes_event_buffer(tmp_path, frozen_now):
    state = {}
    component.handle_value(start_value(), tmp_path, state)
    assert state[events.EVENTS_KEY] == []
    assert state[events.STARTED_SERVER_KEY] == pytest.approx(STARTED_MS + 150.0)


def test_stop_writes_buffered_events_into_zip(tmp_path, frozen_now):
    state = {}
    component.handle_value(start_value(), tmp_path, state)
    state[events.EVENTS_KEY].append(
        {"type": "query", "t_ms": 1200, "payload": {"question": "hi"}}
    )
    path = component.handle_value(stop_value(), tmp_path, state)
    with zipfile.ZipFile(path) as zf:
        data = json.loads(zf.read("events.json"))
    assert data["events"] == [
        {"type": "query", "t_ms": 1200, "payload": {"question": "hi"}}
    ]


def test_stop_preserves_events_when_write_fails(tmp_path, frozen_now, monkeypatch):
    state = {}
    component.handle_value(start_value(), tmp_path, state)
    state[events.EVENTS_KEY].append({"type": "query", "t_ms": 1, "payload": {}})
    original = component.session.write_session_zip

    def boom(*args, **kwargs):
        raise OSError

    monkeypatch.setattr(component.session, "write_session_zip", boom)
    with pytest.raises(OSError):
        component.handle_value(stop_value(), tmp_path, state)
    assert state[events.EVENTS_KEY] == [{"type": "query", "t_ms": 1, "payload": {}}]

    monkeypatch.setattr(component.session, "write_session_zip", original)
    path = component.handle_value(stop_value(), tmp_path, state)
    with zipfile.ZipFile(path) as zf:
        data = json.loads(zf.read("events.json"))
    assert data["events"] == [{"type": "query", "t_ms": 1, "payload": {}}]


def test_stop_clears_recording_state(tmp_path, frozen_now):
    state = {}
    component.handle_value(start_value(), tmp_path, state)
    component.handle_value(stop_value(), tmp_path, state)
    assert events.STARTED_SERVER_KEY not in state
    assert events.EVENTS_KEY not in state


def test_missing_voice_handled(tmp_path, frozen_now):
    value = stop_value()
    value["voice_b64"] = None
    path = component.handle_value(value, tmp_path, {})
    with zipfile.ZipFile(path) as zf:
        assert "voice.webm" not in zf.namelist()
