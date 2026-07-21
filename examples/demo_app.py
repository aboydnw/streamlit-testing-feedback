import streamlit as st

import streamlit_testing_feedback as stf


def page_a():
    st.title("Demo page A")
    if st.button("Do a thing"):
        st.write("thing done")


def page_b():
    st.title("Demo page B")
    st.slider("A slider", 0, 10)


with st.sidebar:
    zip_path = stf.feedback_recorder(dir=".feedback")
if zip_path:
    st.sidebar.success(f"session saved: {zip_path.name}")

pages = st.navigation([st.Page(page_a, title="A"), st.Page(page_b, title="B")])
pages.run()
