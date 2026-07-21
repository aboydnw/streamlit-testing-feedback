# streamlit-testing-feedback

A riffrec-style product-testing recorder for Streamlit apps. Captures screen
video + voice narration in the browser and writes a session zip into the
consuming project's `.feedback/` directory for agent-driven analysis.

**Status: pre-release.** Consume via path/git dependency; no PyPI yet.

## Headless-VM gotcha

`getDisplayMedia` requires a secure context. If the Streamlit server runs on a
remote VM, `http://<vm-ip>:8501` silently blocks screen capture. Tunnel it:

    ssh -N -L 8501:localhost:8501 dev-server

then open http://localhost:8501.
