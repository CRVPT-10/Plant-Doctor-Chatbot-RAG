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
        
        # 2. Custom Navigation pills using Streamlit Buttons
        st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #90a4ae; margin-bottom: 5px; margin-top: 25px;'>NAVIGATION</p>", unsafe_allow_html=True)
        
        pages = [
            {"label": "💬 Chat Assistant", "name": "Chat Assistant"},
            {"label": "🏛️ Govt Schemes", "name": "Govt Schemes"},
            {"label": "📤 Ingestion Panel", "name": "Ingestion Panel"},
            {"label": "📄 Document Library", "name": "Document Library"},
            {"label": "⚙️ Settings", "name": "Settings"}
        ]
        
        for p in pages:
            is_active = st.session_state.current_page == p["name"]
            if st.button(
                p["label"], 
                key=f"nav_{p['name']}", 
                type="primary" if is_active else "secondary", 
                use_container_width=True
            ):
                st.session_state.current_page = p["name"]
                st.rerun()
        
        # Fetch status details from Client
        health_status = api_client.get_health()
        
        # 3. System Status indicators
        is_server_offline = health_status.get("status") == "offline"
        
        index_ready = health_status.get("govt_schemes_index_ready", False) if st.session_state.current_page == "Govt Schemes" else health_status.get("faiss_index_ready", False)
        index_val = "Offline" if is_server_offline else ("Ready" if index_ready else "Empty")
        llm_val = "Offline" if is_server_offline else ("Connected" if health_status.get("ollama_ready", False) else "Offline")
        embed_val = "Offline" if is_server_offline else ("Ready" if health_status.get("faiss_index_ready", False) else "Empty")
        voice_val = "Offline" if is_server_offline else ("Ready" if health_status.get("ollama_ready", False) else "Offline")
        
        st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #90a4ae; margin-bottom: 5px; margin-top: 25px;'>SYSTEM STATUS</p>", unsafe_allow_html=True)
        status_html = f"""
        <div class="status-panel">
            <div class="status-row">
                <span style="color: #90a4ae;">{"Schemes Index" if st.session_state.current_page == "Govt Schemes" else "FAISS Index"}</span>
                <span class="{"status-value-ready" if index_val == "Ready" else "status-value-offline"}">{index_val}</span>
            </div>
            <div class="status-row">
                <span style="color: #90a4ae;">Ollama (LLM)</span>
                <span class="{"status-value-ready" if llm_val == "Connected" else "status-value-offline"}">{llm_val}</span>
            </div>
            <div class="status-row">
                <span style="color: #90a4ae;">Embeddings</span>
                <span class="{"status-value-ready" if embed_val == "Ready" else "status-value-offline"}">{embed_val}</span>
            </div>
            <div class="status-row">
                <span style="color: #90a4ae;">Voice Engine</span>
                <span class="{"status-value-ready" if voice_val == "Ready" else "status-value-offline"}">{voice_val}</span>
            </div>
        </div>
        """
        st.markdown(status_html, unsafe_allow_html=True)
        
        # 4. Quick Statistics panel
        st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #90a4ae; margin-bottom: 5px; margin-top: 25px;'>QUICK STATS</p>", unsafe_allow_html=True)
        if is_server_offline:
            stats_html = """
            <div class="stats-card">
                <div class="status-row">
                    <span style="color: #90a4ae;">Indexed Documents</span>
                    <span style="font-weight: 600; color: #ff5252;">Offline</span>
                </div>
                <div class="status-row">
                    <span style="color: #90a4ae;">Total Chunks</span>
                    <span style="font-weight: 600; color: #ff5252;">Offline</span>
                </div>
                <div class="status-row">
                    <span style="color: #90a4ae;">Model</span>
                    <span style="font-weight: 600; color: #90a4ae;">Unknown</span>
                </div>
            </div>
            """
        else:
            if st.session_state.current_page == "Govt Schemes":
                indexed_docs = health_status.get("govt_schemes_indexed", [])
            else:
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
            success = api_client.clear_history(st.session_state.session_id)
            st.session_state.chat_history = []
            st.session_state.playing_audio = None
            st.session_state.last_text_query = ""
            if success:
                st.success("Conversation history cleared.")
            else:
                st.warning("Cleared screen, but backend server could not be reached.")
            st.rerun()
                
    return lang_code, health_status
