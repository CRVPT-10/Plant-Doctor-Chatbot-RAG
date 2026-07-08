import streamlit as st
from backend.client import PlantDoctorAPIClient

def render_chat_input(api_client: PlantDoctorAPIClient, lang_code: str, api_url: str):
    """
    Renders input card and buttons row, processes text/voice submissions, and autoplays audio.
    """
    st.markdown("<div class='input-wrapper'>", unsafe_allow_html=True)
    
    text_query = st.text_input(
        "Ask anything about crops, diseases, fertilizers...",
        placeholder="Type your question here...",
        label_visibility="collapsed",
        key="chat_text_input"
    )
    
    btn_cols = st.columns([2, 2, 2, 3, 2])
    with btn_cols[0]:
        img_upload = st.button("📷 Image", use_container_width=True, type="secondary")
    with btn_cols[1]:
        # Mic recorder component
        from streamlit_mic_recorder import mic_recorder
        audio_data = mic_recorder(
            start_prompt="🎤 Voice",
            stop_prompt="⏹️ Stop",
            key="voice_recorder_widget",
            just_once=True
        )
    with btn_cols[2]:
        translate_btn = st.button("🌐 Translate", use_container_width=True, type="secondary")
        
    with btn_cols[4]:
        send_btn = st.button("🚀 Send", use_container_width=True, type="primary")
        
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Audio autoplay player
    if st.session_state.playing_audio:
        full_audio_url = f"{api_url}{st.session_state.playing_audio}"
        st.markdown("<div style='margin-top: 15px;'>", unsafe_allow_html=True)
        st.audio(full_audio_url, autoplay=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    # Process submissions
    submit_query = False
    is_voice = False
    
    if text_query.strip() and text_query != st.session_state.last_text_query and send_btn:
        st.session_state.last_text_query = text_query
        submit_query = True
        is_voice = False
        
    if audio_data is not None and "last_recorded_audio" not in st.session_state:
        st.session_state.last_recorded_audio = audio_data
        submit_query = True
        is_voice = True
    elif audio_data is None and "last_recorded_audio" in st.session_state:
        del st.session_state.last_recorded_audio
        
    if submit_query:
        with st.spinner("Analyzing agricultural database..."):
            try:
                if is_voice:
                    audio_bytes = audio_data["bytes"]
                    res = api_client.voice_query(audio_bytes, st.session_state.session_id, lang_code)
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
                        if audio_url:
                            st.session_state.playing_audio = audio_url
                        st.rerun()
                else:
                    res = api_client.chat_query(text_query, st.session_state.session_id, lang_code)
                    answer = res.get("answer", "")
                    audio_url = res.get("audio_url", "")
                    
                    st.session_state.chat_history.append({
                        "farmer": text_query,
                        "doctor": answer,
                        "audio_url": audio_url,
                        "sources": res.get("sources", []),
                        "confidence": res.get("confidence", 0.0),
                        "metrics": res.get("metrics", {})
                    })
                    if audio_url:
                        st.session_state.playing_audio = audio_url
                    st.rerun()
            except Exception as e:
                st.error(f"Could not connect to API server: {e}")
