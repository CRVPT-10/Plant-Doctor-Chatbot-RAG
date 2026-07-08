import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from streamlit_mic_recorder import mic_recorder
from app.ui import inject_custom_css
from voice.language import SUPPORTED_LANGUAGES, get_language_code

# FastAPI Backend Address
API_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Plant Doctor Chatbot",
    page_icon="🍃",
    layout="wide"
)

# Inject custom Google Fonts and custom CSS styles
inject_custom_css()

# Session State Initialization
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "playing_audio" not in st.session_state:
    st.session_state.playing_audio = None

# Title Header
st.markdown("<h1 style='text-align: center; margin-bottom: 2px;'>🍃 Plant Doctor Chatbot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #a5d6a7; margin-bottom: 30px;'>Multilingual Voice-Enabled AI Assistant for Farmers</p>", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    # 1. Select Language
    selected_lang_name = st.selectbox(
        "Choose Language",
        options=list(SUPPORTED_LANGUAGES.values()),
        index=0
    )
    lang_code = get_language_code(selected_lang_name)
    
    st.markdown("---")
    st.markdown("### 📂 Ingestion Panel")
    
    # 2. Upload Document
    uploaded_file = st.file_uploader(
        "Upload Agricultural Manual (PDF, DOCX, TXT, MD)",
        type=["pdf", "docx", "txt", "md"]
    )
    if uploaded_file is not None:
        if st.button("Index Document", use_container_width=True):
            with st.spinner("Parsing and indexing document..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    resp = requests.post(f"{API_URL}/upload", files=files, timeout=300)
                    if resp.status_code == 200:
                        res = resp.json()
                        st.success(f"Success! Created {res['chunks_created']} chunks.")
                    else:
                        st.error(f"Upload failed: {resp.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error connecting to backend: {e}")
                    
    # 3. Rebuild Database Index
    if st.button("🔄 Rebuild Full Index", use_container_width=True):
        with st.spinner("Rebuilding FAISS index..."):
            try:
                resp = requests.post(f"{API_URL}/embed")
                if resp.status_code == 200:
                    st.success("FAISS index rebuilt successfully!")
                else:
                    st.error("Rebuild failed.")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")
                
    st.markdown("---")
    st.markdown("### 🧹 Actions")
    
    # 4. Clear Chat Memory
    if st.button("Clear Conversation", use_container_width=True):
        try:
            requests.delete(f"{API_URL}/history", params={"session_id": st.session_state.session_id})
            st.session_state.chat_history = []
            st.session_state.playing_audio = None
            st.success("Conversation history cleared.")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing memory: {e}")

    # Display Index Info
    st.markdown("---")
    try:
        health_resp = requests.get(f"{API_URL}/health", timeout=5.0)
        if health_resp.status_code == 200:
            status = health_resp.json()
            st.markdown(f"**FAISS Status:** Ready ✅" if status["faiss_index_ready"] else "**FAISS Status:** Empty ❌")
            st.markdown(f"**Ollama status:** {'Connected ✅' if status['ollama_ready'] else 'Offline ❌'}")
            
            docs_indexed = status.get("documents_indexed", [])
            if docs_indexed:
                st.markdown("**Indexed Documents:**")
                for doc in docs_indexed:
                    st.markdown(f"- {doc['source']} ({doc['chunks_count']} chunks, {doc['language']})")
            else:
                st.markdown("*No documents indexed yet.*")
    except Exception as e:
        st.markdown(f"**System status:** Offline ⚠️ (Error: {e})")

# ----------------- MAIN PANEL -----------------

# Fetch history on startup/reload to keep synced
if not st.session_state.chat_history:
    try:
        hist_resp = requests.get(f"{API_URL}/history", params={"session_id": st.session_state.session_id}, timeout=5.0)
        if hist_resp.status_code == 200:
            for turn in hist_resp.json().get("history", []):
                st.session_state.chat_history.append({
                    "farmer": turn["farmer"],
                    "doctor": turn["plant_doctor"]
                })
    except Exception:
        pass

# Display Messages Container
messages_container = st.container()

with messages_container:
    # Initial Greeting if empty
    if not st.session_state.chat_history:
        st.markdown(
            f'<div class="chat-bubble doctor-bubble">'
            f'👋 Hello! I am your <b>Plant Doctor</b>. Ask me any question about crop diseases, pests, fertilizers, '
            f'or agricultural guidelines. You can type below or click the microphone to speak to me in '
            f'<b>{selected_lang_name}</b>.'
            f'</div>',
            unsafe_allow_html=True
        )
        
    for chat in st.session_state.chat_history:
        # Display Farmer Query
        st.markdown(
            f'<div class="chat-bubble farmer-bubble">'
            f'🌾 {chat["farmer"]}'
            f'</div>',
            unsafe_allow_html=True
        )
        # Display Doctor Response
        st.markdown(
            f'<div class="chat-bubble doctor-bubble">'
            f'🧑‍⚕️ <b>Plant Doctor:</b><br>{chat["doctor"]}'
            f'</div>',
            unsafe_allow_html=True
        )

# ---------------- INPUT CONTROL ----------------

st.markdown("### ✍️ Ask a Question")
input_cols = st.columns([1, 8])

# 1. Voice input widget
with input_cols[0]:
    # Streamlit Mic Recorder custom component
    audio_data = mic_recorder(
        start_prompt="🎤",
        stop_prompt="⏹️",
        key="voice_recorder",
        just_once=True
    )

# 2. Text input box
with input_cols[1]:
    text_query = st.text_input(
        "Type your question here...",
        label_visibility="collapsed",
        key="text_query_input"
    )

submit_query = False
is_voice = False

if audio_data is not None and "last_audio" not in st.session_state:
    # Detect new audio recorded
    st.session_state.last_audio = audio_data
    submit_query = True
    is_voice = True
elif audio_data is None and "last_audio" in st.session_state:
    # Reset tracking
    del st.session_state.last_audio

if text_query.strip() and st.session_state.get("last_text_query") != text_query:
    # Detect new text query
    st.session_state.last_text_query = text_query
    submit_query = True
    is_voice = False

# Process query submissions
if submit_query:
    with st.spinner("Analyzing..."):
        try:
            if is_voice:
                # Save bytes to send multipart post
                audio_bytes = audio_data["bytes"]
                files = {"file": ("query.wav", audio_bytes, "audio/wav")}
                data = {"session_id": st.session_state.session_id}
                
                resp = requests.post(f"{API_URL}/voice", files=files, data=data)
                if resp.status_code == 200:
                    res = resp.json()
                    transcription = res.get("transcription", "")
                    answer = res.get("answer", "")
                    audio_url = res.get("audio_url", "")
                    
                    if transcription:
                        st.session_state.chat_history.append({
                            "farmer": transcription,
                            "doctor": answer,
                            "audio_url": audio_url,
                            "sources": res.get("sources", []),
                            "confidence": res.get("confidence", 0.0),
                            "metrics": res.get("metrics", {})
                        })
                        st.session_state.playing_audio = audio_url
                        st.rerun()
                else:
                    st.error("Speech recognition or answer generation encountered an error.")
            else:
                # Text Chat
                payload = {
                    "query": text_query,
                    "session_id": st.session_state.session_id,
                    "language": lang_code
                }
                resp = requests.post(f"{API_URL}/chat", json=payload)
                if resp.status_code == 200:
                    res = resp.json()
                    answer = res.get("answer", "")
                    
                    st.session_state.chat_history.append({
                        "farmer": text_query,
                        "doctor": answer,
                        "audio_url": None, # Text query doesn't generate TTS automatically to save latency
                        "sources": res.get("sources", []),
                        "confidence": res.get("confidence", 0.0),
                        "metrics": res.get("metrics", {})
                    })
                    st.rerun()
                else:
                    st.error("Error processing chat.")
        except Exception as e:
            st.error(f"Could not reach API Server: {e}")

# ---------------- INFO PANEL (SCORES, AUDIO, LATENCY) ----------------

# Display info about the most recent response
if st.session_state.chat_history:
    last_turn = st.session_state.chat_history[-1]
    
    st.markdown("### 📊 Response Inspection")
    info_tabs = st.tabs(["🔊 Voice Response", "🔍 Grounded Citations", "📈 Performance Diagnostics"])
    
    # Tab 1: Voice player
    with info_tabs[0]:
        audio_url = last_turn.get("audio_url")
        if audio_url:
            # Construct backend full URL
            full_audio_url = f"{API_URL}{audio_url}"
            st.write("Play synthesized response:")
            st.audio(full_audio_url)
            st.markdown(f"[Download Speech Audio File 📥]({full_audio_url})")
        else:
            # Offer text-to-speech creation for text responses
            if st.button("Generate Voice Speech 🔊"):
                with st.spinner("Synthesizing voice..."):
                    # We can fetch voice bytes from API
                    # Let's hit backend text-to-speech if we want, or run it through /chat redirect.
                    # Since we want to support it: we can call voice synthesis. Let's send text query to /voice
                    # or implement a TTS direct API. Since our API supports /voice, let's keep it simple: 
                    # we can prompt the user that TTS is triggered natively on voice queries, 
                    # or make it automatic.
                    pass
            st.info("Speech audio is automatically generated for voice queries. Ask a question using the 🎤 icon above.")
            
    # Tab 2: Citations and Confidence
    with info_tabs[1]:
        confidence = last_turn.get("confidence", 0.0)
        sources = last_turn.get("sources", [])
        
        # Display Confidence
        st.markdown(f"**Contextual Confidence Score:** {confidence*100:.1f}%")
        st.progress(float(confidence))
        
        if sources:
            st.markdown("**Grounded Sources Used:**")
            for idx, src in enumerate(sources):
                score_label = f"Score: {src.get('score', 0.0):.4f}"
                if src.get("rerank_score") is not None:
                    score_label += f" | Rerank Score: {src.get('rerank_score'):.4f}"
                    
                st.markdown(
                    f'<div class="source-card">'
                    f'<div class="source-header">'
                    f'<span>📄 {src.get("source")} (Page {src.get("page", "N/A")})</span>'
                    f'<span class="source-score">{score_label}</span>'
                    f'</div>'
                    f'<div style="font-size: 0.9em; color: #b0bec5; font-style: italic;">'
                    f'"{src.get("content")}"'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.warning("No grounding sources were retrieved from the agriculture document database. Grounded responses may not be reliable.")
            
    # Tab 3: Performance metrics
    with info_tabs[2]:
        metrics = last_turn.get("metrics", {})
        if metrics:
            st.markdown("**Latency Breakdown:**")
            st.write(f"- 📁 Retrieval latency: `{metrics.get('retrieval_time_sec', 0.0)*1000:.1f} ms`")
            st.write(f"- 🧠 Cross-Encoder Rerank latency: `{metrics.get('rerank_score', 0.0)*1000:.1f} ms`" if metrics.get('rerank_time_sec') else "- Rerank: Disabled")
            st.write(f"- 🤖 LLM Inference latency: `{metrics.get('llm_inference_time_sec', 0.0)*1000:.1f} ms`")
            st.write(f"- ⏱️ End-to-End latency: `{metrics.get('total_time_sec', 0.0):.3f} seconds`")
            st.write(f"- 💾 Cached response: `{metrics.get('cached', False)}`")
        else:
            st.info("No metrics logged for this response.")
