import json
import zipfile

from streamlit_testing_feedback import session

STARTED_MS = 1753100000000.0


def make_meta(**overrides):
    kwargs = dict(
        app_url="http://localhost:8501/corpus",
        started_at_ms=STARTED_MS,
        duration_ms=61250.0,
        clock_offset_ms=143.7,
    )
    kwargs.update(overrides)
    return session.build_session_meta(**kwargs)


def test_session_meta_has_all_required_fields():
    meta = make_meta()
    assert meta["recorder"] == "streamlit-testing-feedback"
    assert meta["schema_version"] == session.SCHEMA_VERSION
    assert meta["app_url"] == "http://localhost:8501/corpus"
    assert meta["page"] == "/corpus"
    assert meta["started_at"] == "2025-07-21T12:13:20+00:00"
    assert meta["duration_ms"] == 61250.0
    assert meta["clock_offset_ms"] == 144
    assert meta["recorder_version"]


def test_zip_has_riffrec_layout(tmp_path):
    path = session.write_session_zip(
        tmp_path / ".feedback",
        recording=b"WEBMDATA",
        voice=b"VOICEDATA",
        session=make_meta(),
    )
    with zipfile.ZipFile(path) as zf:
        assert sorted(zf.namelist()) == [
            "events.json",
            "recording.webm",
            "session.json",
            "voice.webm",
        ]
        assert zf.read("recording.webm") == b"WEBMDATA"
        assert json.loads(zf.read("session.json"))["duration_ms"] == 61250.0


def test_zip_name_format(tmp_path):
    path = session.write_session_zip(
        tmp_path, recording=b"x", voice=b"y", session=make_meta()
    )
    assert path.name.startswith("stf-")
    assert path.suffix == ".zip"
    stem = path.name.removeprefix("stf-").removesuffix(".zip")
    date_part, short_id = stem.rsplit("-", 1)
    assert len(short_id) == 6
    assert len(date_part.split("-")) == 4


def test_missing_voice_omits_entry(tmp_path):
    path = session.write_session_zip(
        tmp_path, recording=b"x", voice=None, session=make_meta()
    )
    with zipfile.ZipFile(path) as zf:
        assert "voice.webm" not in zf.namelist()


def test_events_envelope_empty_by_default(tmp_path):
    path = session.write_session_zip(
        tmp_path, recording=b"x", voice=b"y", session=make_meta()
    )
    with zipfile.ZipFile(path) as zf:
        events = json.loads(zf.read("events.json"))
    assert events == {"schema_version": session.SCHEMA_VERSION, "events": []}


def test_creates_feedback_dir(tmp_path):
    target = tmp_path / "nested" / ".feedback"
    path = session.write_session_zip(
        target, recording=b"x", voice=b"y", session=make_meta()
    )
    assert path.parent == target
