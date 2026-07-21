# streamlit-testing-feedback

A riffrec-style product-testing recorder for Streamlit apps. Captures screen
video + voice narration in the browser and writes a session zip into the
consuming project's `.feedback/` directory for agent-driven analysis.

**Status: pre-release.** Consume via path/git dependency; no PyPI yet.

## Usage

    import streamlit_testing_feedback as stf

    stf.feedback_recorder(dir=".feedback")            # sidebar record button
    stf.log_event("query", question=q)                # no-op unless recording
    with stf.instrument("retrieval", k=5):            # timed event (+ok flag)
        ...

Events land in the zip's `events.json` as `{type, t_ms, payload}` with `t_ms`
relative to recording start, clock-offset corrected against the video.

## Headless-VM gotcha

`getDisplayMedia` requires a secure context. If the Streamlit server runs on a
remote VM, `http://<vm-ip>:8501` silently blocks screen capture. Tunnel it:

    ssh -N -L 8501:localhost:8501 dev-server

then open http://localhost:8501.
