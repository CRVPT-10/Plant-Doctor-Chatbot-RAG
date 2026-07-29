import os
import sys
import uuid
import streamlit as st

# Add project root directory to path to support absolute imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.client import PlantDoctorAPIClient
from utils.ui_helpers import load_css_stylesheets
from components.sidebar import render_sidebar
from components.hero import render_hero_header
from components.chat_window import render_chat_window
from components.chat_input import render_chat_input
from components.confidence_card import render_confidence_card
from components.diagnostics import render_diagnostics_card
from components.history_panel import render_recent_history_panel

# 1. Initialize API Client
API_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
api_client = PlantDoctorAPIClient(base_url=API_URL)

# 2. Inject CSS Stylesheets
load_css_stylesheets()

# 3. Session State Initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "playing_audio" not in st.session_state:
    st.session_state.playing_audio = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Chat Assistant"
if "last_text_query" not in st.session_state:
    st.session_state.last_text_query = ""

# 4. Load Conversation History on startup
if not st.session_state.chat_history:
    try:
        history = api_client.get_history(st.session_state.session_id)
        for turn in history:
            # Format historical logs into UI list schema
            st.session_state.chat_history.append({
                "farmer": turn["farmer"],
                "doctor": turn["plant_doctor"],
                "audio_url": None,
                "sources": [],
                "confidence": 0.5,
                "metrics": {}
            })
    except Exception:
        pass

# 5. Render Sidebar & Retrieve configurations
lang_code, health_status = render_sidebar(api_client)

# 6. Render Active Page Component
if st.session_state.current_page == "Chat Assistant":
    main_cols = st.columns([7, 3])
    
    # Left Column: Chat log + input controls
    with main_cols[0]:
        render_hero_header()
        
        # Selected language display name maps back for greeting labels
        lang_names = {"en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil"}
        selected_lang_name = lang_names.get(lang_code, "English")
        
        render_chat_window(selected_lang_name)
        render_chat_input(api_client, lang_code, API_URL)
        
    # Right Column: Diagnostics, confidence ring, history
    with main_cols[1]:
        last_turn = st.session_state.chat_history[-1] if st.session_state.chat_history else None
        render_confidence_card(last_turn)
        render_diagnostics_card(last_turn)
        render_recent_history_panel()

elif st.session_state.current_page == "Govt Schemes":
    st.markdown("<h2>🏛️ Government Schemes & Benefits</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #90a4ae;'>Discover available government schemes, subsidies, and credit loans. Filter by criteria or ask the AI assistant directly.</p>", unsafe_allow_html=True)
    
    import json
    schemes_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "govt_schemes", "schemes_list.json")
    try:
        with open(schemes_json_path, "r", encoding="utf-8") as f:
            schemes = json.load(f)
    except Exception as e:
        schemes = []
        st.error(f"Failed to load schemes: {e}")
        
    # 1. Filters Card
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("<h4>🔍 Filter Schemes</h4>", unsafe_allow_html=True)
    
    filter_cols = st.columns(3)
    with filter_cols[0]:
        state_list = ["All", "Telangana", "Andhra Pradesh", "Uttar Pradesh", "Maharashtra", "Karnataka", "Tamil Nadu", "Gujarat"]
        selected_state = st.selectbox("Select State", state_list, index=0)
    with filter_cols[1]:
        crop_list = ["All", "Paddy", "Cotton", "Wheat", "Maize", "Groundnut", "Sugarcane", "Potato", "Onion"]
        selected_crop = st.selectbox("Select Crop Focus", crop_list, index=0)
    with filter_cols[2]:
        cat_list = ["All", "Income Support", "Insurance", "Irrigation", "Soil Health", "Agricultural Marketing", "Credit & Loans", "Horticulture", "Mechanization & Allied", "Farmer Groups", "Infrastructure", "Natural Farming"]
        selected_cat = st.selectbox("Select Scheme Category", cat_list, index=0)
        
    # Eligibility tags
    st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #90a4ae; margin-top: 10px; margin-bottom: 5px;'>ELIGIBILITY TAGS</p>", unsafe_allow_html=True)
    elig_cols = st.columns(4)
    with elig_cols[0]:
        is_small = st.checkbox("Small Farmers", value=False)
    with elig_cols[1]:
        is_marginal = st.checkbox("Marginal Farmers", value=False)
    with elig_cols[2]:
        is_tenant = st.checkbox("Tenant Farmers", value=False)
    with elig_cols[3]:
        is_fpo = st.checkbox("FPOs / Groups", value=False)
        
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Filter schemes logic
    filtered_schemes = []
    for s in schemes:
        if selected_state != "All" and "All" not in s["states"] and selected_state not in s["states"]:
            continue
        if selected_crop != "All" and "All" not in s["crops"] and selected_crop not in s["crops"]:
            continue
        if selected_cat != "All" and s["category"] != selected_cat:
            continue
        if is_small and "Small Farmers" not in s["eligibility"]:
            continue
        if is_marginal and "Marginal Farmers" not in s["eligibility"]:
            continue
        if is_tenant and "Tenant Farmers" not in s["eligibility"]:
            continue
        if is_fpo and "FPOs" not in s["eligibility"] and "Farmer Groups" not in s["category"]:
            continue
        filtered_schemes.append(s)
        
    # Render matching scheme cards
    st.markdown(f"<h4>📋 Available Matching Schemes ({len(filtered_schemes)})</h4>", unsafe_allow_html=True)
    if filtered_schemes:
        for idx in range(0, len(filtered_schemes), 3):
            cols = st.columns(3)
            for col_idx in range(3):
                if idx + col_idx < len(filtered_schemes):
                    s = filtered_schemes[idx + col_idx]
                    with cols[col_idx]:
                        badges = "".join(f'<span class="badge">{tag}</span>' for tag in s["eligibility"][:3])
                        st.markdown(
                            f'<div class="scheme-card">'
                            f'  <div class="scheme-card-header">'
                            f'    <span class="scheme-card-icon">🏛️</span>'
                            f'    <span class="scheme-card-title">{s["title"]}</span>'
                            f'  </div>'
                            f'  <div class="scheme-card-body">'
                            f'    <div class="scheme-card-fullname">{s["fullName"]}</div>'
                            f'    <p class="scheme-card-desc">{s["description"]}</p>'
                            f'    <div class="scheme-card-badges">{badges}</div>'
                            f'  </div>'
                            f'  <div class="scheme-card-footer">'
                            f'    <a class="scheme-card-link" href="{s["url"]}" target="_blank">Know More ➔</a>'
                            f'  </div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
    else:
        st.info("No government schemes match the selected filters. Try broadening your filter selection.")
        
    st.markdown("<hr style='border: 1px solid #16242e; margin: 35px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3>💬 Ask AI about Govt Schemes</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #90a4ae; font-size: 0.85rem;'>Get details about subsidies, documents required, and eligibility rules for the selected schemes.</p>", unsafe_allow_html=True)
    
    main_cols = st.columns([7, 3])
    with main_cols[0]:
        render_hero_header()
        lang_names = {"en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil"}
        selected_lang_name = lang_names.get(lang_code, "English")
        render_chat_window(selected_lang_name)
        render_chat_input(api_client, lang_code, API_URL)
    with main_cols[1]:
        last_turn = st.session_state.chat_history[-1] if st.session_state.chat_history else None
        render_confidence_card(last_turn)
        render_diagnostics_card(last_turn)
        render_recent_history_panel()

elif st.session_state.current_page == "Ingestion Panel":
    st.markdown("<h2>📤 Manual Ingestion Workspace</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #90a4ae;'>Add new agricultural manuals, research pamphlets, or guideline text books directly into the vector database.</p>", unsafe_allow_html=True)
    
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("<h4>Upload New Document File</h4>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload manual (PDF, DOCX, TXT, MD)",
        type=["pdf", "docx", "txt", "md"],
        label_visibility="collapsed"
    )
    if uploaded_file is not None:
        if st.button("🚀 Parse & Index Document", use_container_width=True, type="primary"):
            with st.spinner("Processing document (extracting, chunking, embedding, indexing)..."):
                try:
                    res = api_client.upload_document(
                        uploaded_file.name, 
                        uploaded_file.getvalue(), 
                        uploaded_file.type
                    )
                    st.success(f"Success! Indexed '{uploaded_file.name}' into {res['chunks_created']} semantic chunks.")
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("<h4>Rebuild Entire Vector Store</h4>", unsafe_allow_html=True)
    st.markdown("<p style='color: #90a4ae; font-size: 0.85rem;'>Forces a complete rebuild of the vector search FAISS index and SQLite metadata stores from files inside the 'data/documents/' directory.</p>", unsafe_allow_html=True)
    if st.button("🔄 Rebuild Full Index", type="secondary", use_container_width=True):
        with st.spinner("Rebuilding indexes (this may take a minute)..."):
            if api_client.rebuild_index():
                st.success("Vector DB Index and SQLite metadata table rebuilt successfully!")
            else:
                st.error("Rebuild failed.")
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.current_page == "Document Library":
    st.markdown("<h2>📄 Grounded Document Library</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #90a4ae;'>The following reference texts are indexed in the FAISS vector database and used to answer farmer questions.</p>", unsafe_allow_html=True)
    
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    indexed_docs = health_status.get("documents_indexed", [])
    if indexed_docs:
        for doc in indexed_docs:
            st.markdown(
                f'<div style="display: flex; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid #16242e;">'
                f'  <div style="display: flex; flex-direction: column;">'
                f'    <span style="font-weight: 600; color: #ffffff;">📄 {doc["source"]}</span>'
                f'    <span style="font-size: 0.78rem; color: #90a4ae;">ID: {doc["doc_id"]}</span>'
                f'  </div>'
                f'  <div style="display: flex; gap: 15px; align-items: center;">'
                f'    <span style="background-color: rgba(0, 168, 107, 0.12); color: #00a86b; padding: 4px 10px; border-radius: 8px; font-size: 0.8rem; font-weight: bold;">{doc["language"].upper()}</span>'
                f'    <span style="font-size: 0.85rem; color: #e3e8ec; font-weight: 500;">{doc["chunks_count"]} semantic chunks</span>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("No documents have been indexed yet. Upload documents using the Ingestion Panel.")
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.current_page == "Settings":
    st.markdown("<h2>⚙️ Application Settings</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #90a4ae;'>Configure models, thresholds, and processing endpoints.</p>", unsafe_allow_html=True)
    
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("<h4>FastAPI API Backend Connection</h4>", unsafe_allow_html=True)
    st.text_input("Backend URL Address", value=API_URL, disabled=True)
    
    st.markdown("<h4 style='margin-top: 25px;'>TTS Voice Profile Setting</h4>", unsafe_allow_html=True)
    st.selectbox("TTS Engine Voice Language", ["English (en-US-GuyNeural)", "Hindi (hi-IN-MadhurNeural)", "Telugu (te-IN-MohanNeural)", "Tamil (ta-IN-ValluvarNeural)"], index=2, disabled=True)
    
    st.markdown("<h4 style='margin-top: 25px;'>Vector Search Configurations</h4>", unsafe_allow_html=True)
    st.write("- Dense Embeddings Model: `BAAI/bge-small-en-v1.5` (CPU)")
    st.write("- Cross-Encoder Reranker: `BAAI/bge-reranker-base` (CPU)")
    st.write("- Hybrid Fusion Search: Enabled (BM25 + FAISS)")
    st.markdown("</div>", unsafe_allow_html=True)
