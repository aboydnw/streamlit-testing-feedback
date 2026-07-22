# streamlit-testing-feedback

A riffrec-style product-testing recorder for Streamlit apps. Captures screen
video + voice narration in the browser, merges them with server-side app
events, and writes a session zip into the consuming project's `.feedback/`
directory — ready for agent-driven analysis.

**Status: pre-release.** Consume via path/git dependency; no PyPI yet.

## Install

```toml
# pyproject.toml of the consuming app
[dependency-groups]
feedback = ["streamlit-testing-feedback"]

[tool.uv.sources]
streamlit-testing-feedback = { path = "../streamlit-testing-feedback", editable = true }
```

```bash
uv sync --group feedback
```

## Usage

```python
import streamlit_testing_feedback as stf

# mount once in the app shell (sidebar recommended — persists across pages)
stf.feedback_recorder(dir=".feedback")

# tier-2 events: no-ops unless a recording is in progress
stf.log_event("query", question=q)
with stf.instrument("retrieval", k=5):
    results = retriever.retrieve(q, k=5)
```

Gitignore `.feedback/` in the consuming project.

## The recording flow

1. **● Record feedback** → a pre-flight panel explains what gets captured and
   reminds the tester to narrate out loud (narration is the highest-signal
   artifact for analysis).
2. **Start recording** → the browser asks for screen + mic permission, then the
   button shows **■ Stop** with a REC dot and elapsed timer.
3. After ~10 minutes a soft warning suggests stopping (the payload rides the
   Streamlit websocket once, at stop — keep sessions reasonably short).
4. **■ Stop** → the zip is written server-side and the button confirms
   `✓ saved stf-….zip`.

## Session zip layout

| File | What it is |
|---|---|
| `session.json` | recorder version, app URL, page, start time, `duration_ms`, `clock_offset_ms` |
| `events.json` | `{schema_version, events: [{type, t_ms, payload}]}` — server-side tier-2 events, `t_ms` relative to recording start, clock-offset corrected against the video |
| `recording.webm` | screen video (no audio track) |
| `voice.webm` | mic narration (absent if the mic was declined) |

`duration_ms` in `session.json` is authoritative — MediaRecorder webm files
carry no duration metadata, so analysis tools should use it to detect a
truncated video read.

## Headless-VM gotcha

`getDisplayMedia` requires a secure context. If the Streamlit server runs on a
remote VM, `http://<vm-ip>:8501` silently blocks screen capture. Tunnel it:

    ssh -N -L 8501:localhost:8501 dev-server

then open http://localhost:8501.

## Analyzing sessions

The zips follow the riffrec layout, so riffrec-style analysis workflows apply:
transcribe `voice.webm` first (e.g. mcp-video-analyzer's `get_transcript`),
corroborate with `events.json`, then pull video frames for the moments that
matter. Events use server-side semantic boundaries (query, index, eval) rather
than browser DOM events — by design.
