import base64
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_spike = components.declare_component(
    "stf_spike", path=str(Path(__file__).parent / "frontend")
)


def handle(value):
    if not value:
        return
    if value["status"] == "recording":
        if st.session_state.get("spike_started") != value["startedAt"]:
            st.session_state["spike_started"] = value["startedAt"]
            offset = time.time() * 1000 - value["startedAt"]
            st.session_state["spike_offset"] = offset
        st.sidebar.caption(
            f"recording — clock offset ~{st.session_state['spike_offset']:.0f}ms"
        )
    elif value["status"] == "stopped":
        if st.session_state.get("spike_written") == value["startedAt"]:
            st.sidebar.success("already written (rerun was idempotent)")
            return
        out = Path(__file__).parent / "out"
        out.mkdir(exist_ok=True)
        rec = base64.b64decode(value["recording_b64"])
        voice = base64.b64decode(value["voice_b64"])
        (out / "recording.webm").write_bytes(rec)
        (out / "voice.webm").write_bytes(voice)
        st.session_state["spike_written"] = value["startedAt"]
        st.sidebar.success(
            f"wrote recording {len(rec) / 1e6:.1f}MB, voice {len(voice) / 1e6:.1f}MB "
            f"({value['duration_ms'] / 1000:.0f}s)"
        )


def page_a():
    st.title("Page A")
    if "count" not in st.session_state:
        st.session_state["count"] = 0
    if st.button("Force rerun"):
        st.session_state["count"] += 1
    st.write(f"Reruns: {st.session_state['count']}")


def page_b():
    st.title("Page B")
    st.write("Switched pages — is the recorder still alive?")


with st.sidebar:
    value = _spike(key="stf_spike", default=None)
handle(value)

pages = st.navigation([st.Page(page_a, title="A"), st.Page(page_b, title="B")])
pages.run()
