import streamlit as st

def inject_custom_css():
    """
    Injects custom Google Fonts and glassmorphic agricultural themed CSS styles.
    """
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Background and Headers */
    .stApp {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        color: #e0e0e0;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: #ffffff;
        text-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3);
    }
    
    /* Sidebar Styles */
    section[data-testid="stSidebar"] {
        background-color: rgba(15, 32, 39, 0.85);
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Chat Message Bubbles */
    .chat-bubble {
        padding: 15px;
        border-radius: 18px;
        margin-bottom: 15px;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.2);
        max-width: 80%;
        line-height: 1.5;
        animation: fadeIn 0.5s ease-out;
    }
    
    .farmer-bubble {
        background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
        color: #ffffff;
        margin-left: auto;
        border-bottom-right-radius: 2px;
    }
    
    .doctor-bubble {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
        margin-right: auto;
        border-bottom-left-radius: 2px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    
    /* Source Cards Styling */
    .source-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 10px;
        border-left: 5px solid #4caf50;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.15);
    }
    
    .source-header {
        font-weight: 600;
        color: #4caf50;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
    }
    
    .source-score {
        background: rgba(76, 175, 80, 0.2);
        color: #a5d6a7;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8em;
    }
    
    /* Confidence Meter */
    .confidence-meter {
        background: rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 8px 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
        margin-bottom: 15px;
    }
    
    .confidence-title {
        font-weight: 600;
        margin-right: 10px;
    }
    
    /* Keyframe Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Streamlit Buttons Style override */
    div.stButton > button {
        background: linear-gradient(135deg, #388e3c 0%, #1b5e20 100%) !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2) !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0px 6px 15px rgba(0, 0, 0, 0.3) !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
