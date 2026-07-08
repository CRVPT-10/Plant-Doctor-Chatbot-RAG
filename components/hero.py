import streamlit as st

def render_hero_header():
    """
    Renders the greeting and subtitle headers.
    """
    st.markdown("<h2 style='margin-bottom: 0px;'>Hello, Farmer! 🌱</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #90a4ae; margin-bottom: 25px;'>I'm Plant Doctor, your multilingual AI assistant for all agricultural queries.</p>", unsafe_allow_html=True)
