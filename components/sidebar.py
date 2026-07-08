import streamlit as st
from backend.client import PlantDoctorAPIClient
from utils.constants import SUPPORTED_LANGUAGES, LANGUAGE_TO_CODE

def render_sidebar(api_client: PlantDoctorAPIClient):
    """
    Renders the custom left sidebar with settings, page routing, system status, and stats.
    """
    with st.sidebar:
        # Logo header
        st.markdown(
            '<div class="sidebar-header">'
            '  <div class="sidebar-logo">🌱</div>'
            '  <div style="display: flex; flex-direction: column;">'
            '    <span style="font-weight: 700; font-size: 1.15rem; line-height: 1.2; color: white;">Plant Doctor</span>'
            '    <span style="font-size: 0.78rem; color: #00a86b; font-weight: 500;">AI Assistant for Farmers</span>'
            '  </div>'
            '</div>',
            unsafe_allow_html=True
        )
        
        # 1. Select Language Dropdown
        st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #90a4ae; margin-bottom: 5px; margin-top: 15px;'>LANGUAGE</p>", unsafe_allow_html=True)
        selected_lang_name = st.selectbox(
            "Choose Language",
            options=list(SUPPORTED_LANGUAGES.values()),
            index=0,
            label_visibility="collapsed"
        )
        lang_code = LANGUAGE_TO_CODE[selected_lang_name]
        
        # 2. Navigation Pills
        st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #90a4ae; margin-bottom: 5px; margin-top: 25px;'>NAVIGATION</p>", unsafe_allow_html=True)
        page_selection = st.radio(
            "Navigation",
            options=["💬 Chat Assistant", "📤 Ingestion Panel", "📄 Document Library", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        page_map = {
            "💬 Chat Assistant": "Chat Assistant",
            "📤 Ingestion Panel": "Ingestion Panel",
            "📄 Document Library": "Document Library",
            "⚙️ Settings": "Settings"
        }
        st.session_state.current_page = page_map[page_selection]
        
        # Fetch status details from Client
        health_status = api_client.get_health()
        
        # 3. System Status indicators
        st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #90a4ae; margin-bottom: 5px; margin-top: 25px;'>SYSTEM STATUS</p>", unsafe_allow_html=True)
        status_html = f"""
        <div class="status-panel">
            <div class="status-row">
                <span style="color: #90a4ae;">FAISS Index</span>
                <span class="status-value-ready">{"Ready" if health_status["faiss_index_ready"] else "Empty"}</span>
            </div>
            <div class="status-row">
                <span style="color: #90a4ae;">Ollama (LLM)</span>
                <span class="{"status-value-ready" if health_status["ollama_ready"] else "status-value-offline"}">
                    {"Connected" if health_status["ollama_ready"] else "Offline"}
                </span>
            </div>
            <div class="status-row">
                <span style="color: #90a4ae;">Embeddings</span>
                <span class="status-value-ready">{"Ready" if health_status["faiss_index_ready"] else "Empty"}</span>
            </div>
            <div class="status-row">
                <span style="color: #90a4ae;">Voice Engine</span>
                <span class="status-value-ready">{"Ready" if health_status["ollama_ready"] else "Offline"}</span>
            </div>
        </div>
        """
        st.markdown(status_html, unsafe_allow_html=True)
        
        # 4. Quick Statistics panel
        st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #90a4ae; margin-bottom: 5px; margin-top: 25px;'>QUICK STATS</p>", unsafe_allow_html=True)
        indexed_docs = health_status.get("documents_indexed", [])
        total_chunks = sum(doc.get("chunks_count", 0) for doc in indexed_docs)
        
        stats_html = f"""
        <div class="stats-card">
            <div class="status-row">
                <span style="color: #90a4ae;">Indexed Documents</span>
                <span style="font-weight: 600; color: #ffffff;">{len(indexed_docs)}</span>
            </div>
            <div class="status-row">
                <span style="color: #90a4ae;">Total Chunks</span>
                <span style="font-weight: 600; color: #ffffff;">{total_chunks:,}</span>
            </div>
            <div class="status-row">
                <span style="color: #90a4ae;">Model</span>
                <span style="font-weight: 600; color: #00a86b;">qwen2.5:7b</span>
            </div>
        </div>
        """
        st.markdown(stats_html, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        
        # 5. Clear Conversation Button
        if st.button("🧹 Clear Conversation", use_container_width=True, type="secondary"):
            if api_client.clear_history(st.session_state.session_id):
                st.session_state.chat_history = []
                st.session_state.playing_audio = None
                st.success("Conversation history cleared.")
                st.rerun()
            else:
                st.error("Failed to clear conversational memory.")
                
    return lang_code, health_status
