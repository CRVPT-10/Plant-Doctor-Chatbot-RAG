import html
import streamlit as st
from utils.ui_helpers import parse_warning_notice, markdown_to_html


def _render_prompt_banner():
    """Thin pill banner shown at the top of the chat column, as in the mockup."""
    st.markdown(
        '<div class="chat-prompt-banner">'
        '  <span class="chat-prompt-icon">🌾</span>'
        '  <span>Ask me anything about crops, diseases, soil, fertilizers, irrigation and more...</span>'
        '</div>',
        unsafe_allow_html=True
    )


def render_chat_window(selected_lang_name: str):
    """
    Renders all chat bubbles, warning notice panels, citation columns, and speech buttons.
    """
    _render_prompt_banner()

    # Render greeting bubble if chat log is empty
    if not st.session_state.chat_history:
        st.markdown(
            f'<div class="msg-row doctor-row">'
            f'  <div class="avatar avatar-bot">🤖</div>'
            f'  <div class="msg-col">'
            f'    <div class="msg-meta"><span class="msg-name">Plant Doctor</span></div>'
            f'    <div class="doctor-bubble">'
            f'      👋 Hello! I am your <b>Plant Doctor</b>. Ask me any question about crop diseases, pests, '
            f'      fertilizers, or agricultural guidelines. You can type below or use voice input to speak to me in '
            f'      <b>{selected_lang_name}</b>.'
            f'    </div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )
        return

    for idx, chat in enumerate(st.session_state.chat_history):
        ts = chat.get("time", "")

        # 1. Farmer Message Bubble (right aligned, avatar on the right)
        st.markdown(
            f'<div class="msg-row user-row">'
            f'  <div class="msg-col msg-col-right">'
            f'    <div class="msg-meta msg-meta-right"><span class="msg-name">You</span>'
            f'      <span class="msg-time">{ts}</span></div>'
            f'    <div class="user-bubble">{html.escape(chat["farmer"])}</div>'
            f'  </div>'
            f'  <div class="avatar avatar-user">🧑‍🌾</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # 2. Plant Doctor Bubble (left aligned, avatar on the left) - single HTML card
        ans = chat["doctor"]
        main_ans, notice_text = parse_warning_notice(ans)
        body_html = markdown_to_html(main_ans)

        # Notice box (inside the card)
        notice_html = ""
        if notice_text:
            notice_html = (
                f'<div class="notice-box"><span>ℹ️</span>'
                f'<span>{html.escape(notice_text)}</span></div>'
            )

        # Sources grid (inside the card)
        sources_html = ""
        sources = chat.get("sources", [])
        if sources:
            cards = ""
            for s_idx, src in enumerate(sources[:3]):
                score_val = src.get("rerank_score")
                if score_val is None:
                    score_val = src.get("score")
                if score_val is None:
                    score_val = 0.0
                src_name = html.escape(str(src.get("source", "Unknown")))
                cards += (
                    f'<div class="source-mini-card">'
                    f'  <div class="source-mini-header">'
                    f'    <span class="source-mini-title">{s_idx + 1}. {src_name}</span>'
                    f'    <span class="source-mini-book">📖</span>'
                    f'  </div>'
                    f'  <div class="source-mini-footer">'
                    f'    <span class="source-mini-page">Page {src.get("page", "N/A")}</span>'
                    f'    <span class="source-mini-score">Score: {score_val:.2f}</span>'
                    f'  </div>'
                    f'</div>'
                )
            sources_html = (
                f'<div class="sources-section-title">Sources ({len(sources)})</div>'
                f'<div class="sources-grid">{cards}</div>'
            )

        actions_html = (
            '<div class="bubble-actions">'
            '  <span class="action-icon-btn" title="Like">👍</span>'
            '  <span class="action-icon-btn" title="Dislike">👎</span>'
            '  <span class="action-icon-btn" title="Copy">📋</span>'
            '  <span class="action-icon-btn" title="Speech">🔊</span>'
            '</div>'
        )

        st.markdown(
            f'<div class="msg-row doctor-row">'
            f'  <div class="avatar avatar-bot">🤖</div>'
            f'  <div class="msg-col doctor-col">'
            f'    <div class="msg-meta"><span class="msg-name">Plant Doctor</span>'
            f'      <span class="msg-time">{ts}</span></div>'
            f'    <div class="doctor-bubble">'
            f'      {body_html}{notice_html}{sources_html}{actions_html}'
            f'    </div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )
