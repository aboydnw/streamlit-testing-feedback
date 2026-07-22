import pytest

from streamlit_testing_feedback import events

STARTED_SERVER_MS = 1753100000150.0


@pytest.fixture
def state(monkeypatch):
    fake_state = {}
    monkeypatch.setattr(events, "_session_state", lambda: fake_state)
    return fake_state


@pytest.fixture
def recording(state, monkeypatch):
    state[events.STARTED_SERVER_KEY] = STARTED_SERVER_MS
    monkeypatch.setattr(
        events.time, "time", lambda: (STARTED_SERVER_MS + 2500) / 1000
    )
    return state


def test_log_event_noop_when_not_recording(state):
    events.log_event("query", question="hi")
    assert events.EVENTS_KEY not in state


def test_is_recording(state):
    assert not events.is_recording()
    state[events.STARTED_SERVER_KEY] = STARTED_SERVER_MS
    assert events.is_recording()


def test_log_event_appends_offset_timestamp(recording):
    events.log_event("query", question="hi")
    assert recording[events.EVENTS_KEY] == [
        {"type": "query", "t_ms": 2500, "payload": {"question": "hi"}}
    ]


def test_log_event_appends_in_order(recording):
    events.log_event("a")
    events.log_event("b")
    assert [e["type"] for e in recording[events.EVENTS_KEY]] == ["a", "b"]


def test_instrument_logs_start_event_on_entry(recording, monkeypatch):
    monkeypatch.setattr(events.time, "perf_counter", lambda: 0.0)
    with events.instrument("eval-sweep"):
        (start,) = recording[events.EVENTS_KEY]
        assert start["type"] == "eval-sweep"
        assert start["payload"]["phase"] == "start"


def test_instrument_logs_start_then_end_ok(recording, monkeypatch):
    ticks = iter([10.0, 10.25])
    monkeypatch.setattr(events.time, "perf_counter", lambda: next(ticks))
    with events.instrument("retrieval", k=5):
        pass
    start, end = recording[events.EVENTS_KEY]
    assert start["payload"] == {"k": 5, "phase": "start"}
    assert end["payload"]["phase"] == "end"
    assert end["payload"]["duration_ms"] == 250
    assert end["payload"]["ok"] is True
    assert end["payload"]["interrupted"] is False
    assert end["payload"]["k"] == 5


def test_instrument_exception_logs_failure_not_interrupted(recording, monkeypatch):
    ticks = iter([10.0, 10.1])
    monkeypatch.setattr(events.time, "perf_counter", lambda: next(ticks))
    with pytest.raises(ValueError):
        with events.instrument("eval"):
            raise ValueError("boom")
    start, end = recording[events.EVENTS_KEY]
    assert start["payload"]["phase"] == "start"
    assert end["payload"]["ok"] is False
    assert end["payload"]["interrupted"] is False


def test_instrument_base_exception_marks_interrupted_and_reraises(recording, monkeypatch):
    ticks = iter([10.0, 10.02])
    monkeypatch.setattr(events.time, "perf_counter", lambda: next(ticks))

    class Interrupt(BaseException):
        pass

    with pytest.raises(Interrupt):
        with events.instrument("eval-sweep"):
            raise Interrupt
    start, end = recording[events.EVENTS_KEY]
    assert start["payload"]["phase"] == "start"
    assert end["payload"]["ok"] is False
    assert end["payload"]["interrupted"] is True


def test_instrument_reserved_payload_keys_overridden(recording, monkeypatch):
    ticks = iter([10.0, 10.2])
    monkeypatch.setattr(events.time, "perf_counter", lambda: next(ticks))
    with events.instrument("x", ok="user-value", duration_ms=999, phase="user"):
        pass
    end = recording[events.EVENTS_KEY][-1]
    assert end["payload"]["ok"] is True
    assert end["payload"]["duration_ms"] == 200
    assert end["payload"]["phase"] == "end"


def test_instrument_noop_when_not_recording(state):
    with events.instrument("retrieval"):
        pass
    assert events.EVENTS_KEY not in state
