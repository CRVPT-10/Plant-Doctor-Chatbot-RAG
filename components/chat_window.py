import streamlit as st
from utils.ui_helpers import parse_warning_notice

def render_chat_window(selected_lang_name: str):
    """
    Renders all chat bubbles, warning notice panels, citation columns, and speech buttons.
    """
    # Render greeting card if chat log is empty
    if not st.session_state.chat_history:
        st.markdown(
            f'<div class="chat-bubble-container doctor-message-container">'
            f'  <div class="chat-meta"><span>🤖 Plant Doctor</span><span>Greeting</span></div>'
            f'  <div class="doctor-bubble">'
            f'    👋 Hello! I am your <b>Plant Doctor</b>. Ask me any question about crop diseases, pests, fertilizers, '
            f'    or agricultural guidelines. You can type below or click the microphone to speak to me in '
            f'    <b>{selected_lang_name}</b>.'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )
        return
        
    for idx, chat in enumerate(st.session_state.chat_history):
        # 1. Farmer Message Bubble
        st.markdown(
            f'<div class="chat-bubble-container user-message-container">'
            f'  <div class="chat-meta"><span>👤 You</span><span>Query</span></div>'
            f'  <div class="user-bubble">🌾 {chat["farmer"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # 2. Plant Doctor Bubble
        ans = chat["doctor"]
        main_ans, notice_text = parse_warning_notice(ans)
        
        st.markdown(
            f'<div class="chat-bubble-container doctor-message-container">'
            f'  <div class="chat-meta"><span>🤖 Plant Doctor</span><span>Response</span></div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # Open response context card container
        with st.container():
            st.markdown('<div class="doctor-bubble">', unsafe_allow_html=True)
            
            # Markdown text
            st.markdown(main_ans)
            
            # Render styled warning notice card
            if notice_text:
                st.markdown(
                    f'<div class="notice-box">'
                    f'  <span>💡</span>'
                    f'  <span>{notice_text}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
            # Horizontal Citations column list (max 3 cards)
            sources = chat.get("sources", [])
            if sources:
                st.markdown(f"<div class='sources-section-title'>Sources ({len(sources)})</div>", unsafe_allow_html=True)
                cols = st.columns(3)
                for s_idx, src in enumerate(sources[:3]):
                    with cols[s_idx]:
                        st.markdown(
                            f'<div class="source-mini-card">'
                            f'  <div class="source-mini-header">'
                            f'    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 80%;">📄 {src.get("source")}</span>'
                            f'    <span>📖</span>'
                            f'  </div>'
                            f'  <div class="source-mini-footer">'
                            f'    <span class="source-mini-page">Page {src.get("page", "N/A")}</span>'
                            f'    <span class="source-mini-score">Score: {src.get("rerank_score", src.get("score", 0.0)):.2f}</span>'
                            f'  </div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        
            # Inline actions toolbar
            st.markdown(
                f'<div class="bubble-actions">'
                f'  <span class="action-icon-btn">👍 Like</span>'
                f'  <span class="action-icon-btn">👎 Dislike</span>'
                f'  <span class="action-icon-btn">📋 Copy</span>'
                f'  <span class="action-icon-btn">🔊 Speech</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
