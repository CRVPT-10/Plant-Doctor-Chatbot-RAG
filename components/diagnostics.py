import streamlit as st

def render_diagnostics_card(last_turn: dict = None):
    """
    Renders performance metrics of retrieval and LLM processing in the right sidebar.
    """
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-header'>⚡ Performance Diagnostics</div>", unsafe_allow_html=True)
    
    metrics = last_turn.get("metrics", {}) if last_turn else {}
    ret_time = f"{metrics.get('retrieval_time_sec', 0.0)*1000:.1f} ms" if metrics else "-- ms"
    rerank_time = f"{metrics.get('rerank_time_sec', 0.0)*1000:.1f} ms" if metrics.get('rerank_time_sec') else "-- ms"
    llm_time = f"{metrics.get('llm_inference_time_sec', 0.0)*1000:.1f} ms" if metrics else "-- ms"
    total_time = f"{metrics.get('total_time_sec', 0.0):.2f} s" if metrics else "-- s"
    
    diag_html = f"""
    <div class="diagnostic-row">
        <span class="diagnostic-label">Retrieval Latency</span>
        <span class="diagnostic-value">{ret_time}</span>
    </div>
    <div class="diagnostic-row">
        <span class="diagnostic-label">Rerank Latency</span>
        <span class="diagnostic-value">{rerank_time}</span>
    </div>
    <div class="diagnostic-row">
        <span class="diagnostic-label">LLM Inference</span>
        <span class="diagnostic-value">{llm_time}</span>
    </div>
    <div class="diagnostic-row" style="border-bottom: none; padding-top: 12px; margin-top: 5px;">
        <span class="diagnostic-label" style="color: #ffffff; font-weight: 600;">Total Response Time</span>
        <span class="diagnostic-value" style="color: #00a86b; font-size: 1rem;">{total_time}</span>
    </div>
    """
    st.markdown(diag_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
