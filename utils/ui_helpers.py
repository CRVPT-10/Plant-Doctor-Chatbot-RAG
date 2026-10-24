import os
import re
import html
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

def _inline_md(text: str) -> str:
    """Escapes HTML, then applies inline markdown (bold / italic)."""
    text = html.escape(text)
    # **bold** and __bold__
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # *italic* (avoid matching bullet markers, which are handled per-line)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", text)
    return text


def markdown_to_html(text: str) -> str:
    """
    Lightweight converter for the subset of markdown the LLM produces
    (bullet lists, numbered lists, bold, paragraphs). Returns safe HTML
    so the whole answer can live inside a single styled card.
    """
    if not text:
        return ""

    lines = text.split("\n")
    html_parts = []
    list_buffer = []

    def flush_list():
        if list_buffer:
            items = "".join(f"<li>{_inline_md(it)}</li>" for it in list_buffer)
            html_parts.append(f"<ul>{items}</ul>")
            list_buffer.clear()

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_list()
            continue
        # Bullet markers: -, *, •  OR numbered: "1." / "1)"
        m = re.match(r"^([-*•]|\d+[.)])\s+(.*)$", line)
        if m:
            list_buffer.append(m.group(2))
        else:
            flush_list()
            html_parts.append(f"<p>{_inline_md(line)}</p>")

    flush_list()
    return "".join(html_parts)


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
