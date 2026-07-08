import streamlit as st

def render_recent_history_panel():
    """
    Renders recent conversation prompts in the right sidebar.
    """
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-header'>⏱️ Recent Conversations</div>", unsafe_allow_html=True)
    
    if st.session_state.chat_history:
        for turn in st.session_state.chat_history[-5:]:
            st.markdown(
                f'<div class="recent-conv-item">'
                f'  <span class="recent-conv-text">{turn["farmer"][:24]}...</span>'
                f'  <span class="recent-conv-time">10:24 AM</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown("<p style='font-size: 0.85rem; color: #546e7a; font-style: italic; text-align: center; margin: 15px 0;'>No interactions recorded yet.</p>", unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
