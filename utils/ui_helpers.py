import os
import streamlit as st
from typing import Tuple

def load_css_stylesheets():
    """
    Reads CSS stylesheet files from the styles/ folder and injects them into Streamlit.
    """
    css_files = ["main.css", "sidebar.css", "chat.css", "cards.css", "animations.css"]
    combined_css = ""
    
    # Locate project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    styles_dir = os.path.join(project_root, "styles")
    
    for filename in css_files:
        filepath = os.path.join(styles_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                combined_css += f.read() + "\n"
                
    if combined_css:
        st.markdown(f"<style>\n{combined_css}\n</style>", unsafe_allow_html=True)

def parse_warning_notice(answer_text: str) -> Tuple[str, str]:
    """
    Searches for lines starting with 'Note:' or local language equivalents 
    and returns a tuple (main_answer, notice_text).
    """
    notice_text = None
    main_answer = answer_text
    
    lines = answer_text.split('\n')
    for line in lines:
        clean = line.strip()
        # Checks Telugu (గమనిక), Hindi (ध्यान दें), Tamil (குறிப்பு)
        if clean.startswith(("Note:", "గమనిక:", "ध्यान दें:", "குறிப்பு:", "గమనిక")):
            notice_text = clean
            main_answer = answer_text.replace(line, "")
            break
            
    return main_answer, notice_text
