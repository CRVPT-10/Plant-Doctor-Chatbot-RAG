import streamlit as st

def render_diagnostics_card(last_turn: dict = None):
    """
    Renders performance metrics of retrieval and LLM processing in the right sidebar.
    Uses flat string concatenation to prevent markdown indentation from creating code blocks.
    """
    metrics = last_turn.get("metrics", {}) if last_turn else {}
    ret_time = f"{metrics.get('retrieval_time_sec', 0.0)*1000:.1f} ms" if metrics else "-- ms"
    rerank_time = f"{metrics.get('rerank_time_sec', 0.0)*1000:.1f} ms" if metrics.get('rerank_time_sec') else "-- ms"
    llm_time = f"{metrics.get('llm_inference_time_sec', 0.0)*1000:.1f} ms" if metrics else "-- ms"
    total_time = f"{metrics.get('total_time_sec', 0.0):.2f} s" if metrics else "-- s"
    
    diag_html = (
        f'<div class="custom-card">'
        f'  <div class="card-header">⚡ Performance Diagnostics</div>'
        f'  <div class="diagnostic-row">'
        f'    <span class="diagnostic-label">Retrieval Latency</span>'
        f'    <span class="diagnostic-value">{ret_time}</span>'
        f'  </div>'
        f'  <div class="diagnostic-row">'
        f'    <span class="diagnostic-label">Rerank Latency</span>'
        f'    <span class="diagnostic-value">{rerank_time}</span>'
        f'  </div>'
        f'  <div class="diagnostic-row">'
        f'    <span class="diagnostic-label">LLM Inference</span>'
        f'    <span class="diagnostic-value">{llm_time}</span>'
        f'  </div>'
        f'  <div class="diagnostic-row" style="border-bottom: none; padding-top: 12px; margin-top: 5px;">'
        f'    <span class="diagnostic-label" style="color: #ffffff; font-weight: 600;">Total Response Time</span>'
        f'    <span class="diagnostic-value" style="color: #00a86b; font-size: 1rem;">{total_time}</span>'
        f'  </div>'
        f'</div>'
    )
    st.markdown(diag_html, unsafe_allow_html=True)
