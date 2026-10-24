import streamlit as st


def render_recent_history_panel():
    """
    Renders recent conversation prompts in the right sidebar, plus a
    'View All History' link that opens the Conversation History page.
    """
    history_items_html = ""
    if st.session_state.chat_history:
        for turn in reversed(st.session_state.chat_history[-5:]):
            text = turn.get("farmer", "")
            preview = (text[:26] + "…") if len(text) > 26 else text
            ts = turn.get("time", "")
            history_items_html += (
                f'<div class="recent-conv-item">'
                f'  <span class="recent-conv-text">{preview}</span>'
                f'  <span class="recent-conv-time">{ts}</span>'
                f'</div>'
            )
    else:
        history_items_html = '<p style="font-size: 0.85rem; color: #546e7a; font-style: italic; text-align: center; margin: 15px 0;">No interactions recorded yet.</p>'

    html_content = (
        f'<div class="custom-card recent-conv-card">'
        f'  <div class="card-header">⏱️ Recent Conversations</div>'
        f'  {history_items_html}'
        f'</div>'
    )
    st.markdown(html_content, unsafe_allow_html=True)

    # "View All History" link -> navigates to the Conversation History page
    if st.button("View All History  ›", key="view_all_history_btn", use_container_width=True):
        st.session_state.current_page = "Conversation History"
        st.rerun()
