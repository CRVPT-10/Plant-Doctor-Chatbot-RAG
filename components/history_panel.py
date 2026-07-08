import streamlit as st

def render_recent_history_panel():
    """
    Renders recent conversation prompts in the right sidebar.
    Uses flat string concatenation to prevent markdown indentation from creating code blocks.
    """
    history_items_html = ""
    if st.session_state.chat_history:
        for turn in st.session_state.chat_history[-5:]:
            history_items_html += (
                f'<div class="recent-conv-item">'
                f'  <span class="recent-conv-text">{turn["farmer"][:24]}...</span>'
                f'  <span class="recent-conv-time">10:24 AM</span>'
                f'</div>'
            )
    else:
        history_items_html = '<p style="font-size: 0.85rem; color: #546e7a; font-style: italic; text-align: center; margin: 15px 0;">No interactions recorded yet.</p>'
        
    html_content = (
        f'<div class="custom-card">'
        f'  <div class="card-header">⏱️ Recent Conversations</div>'
        f'  {history_items_html}'
        f'</div>'
    )
    st.markdown(html_content, unsafe_allow_html=True)
