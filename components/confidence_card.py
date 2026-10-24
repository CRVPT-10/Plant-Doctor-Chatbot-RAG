import streamlit as st

def render_confidence_card(last_turn: dict = None):
    """
    Renders a custom circular progress SVG widget in the right sidebar.
    Uses flat string concatenation to prevent markdown indentation from creating code blocks.
    """
    confidence_val = last_turn.get("confidence", 0.0) if last_turn else 0.0
    confidence_pct = int(confidence_val * 100)
    
    # Speedometer-style 270-degree arc gauge.
    # Full circumference for r=50 is ~314; a 270-degree sweep uses 3/4 of it.
    circumference = 314.0
    arc_fraction = 0.75  # 270 degrees, 90-degree gap at the bottom
    track_len = circumference * arc_fraction
    progress_len = track_len * confidence_val
    # Rotate so the open gap sits centered at the bottom.
    rotation = "transform=\"rotate(135 60 60)\""

    confidence_label = "No Response Yet"
    confidence_color = "#90a4ae"

    if last_turn:
        if confidence_val >= 0.7:
            confidence_label = "High Confidence"
            confidence_color = "#00e676"
        elif confidence_val >= 0.4:
            confidence_label = "Medium Confidence"
            confidence_color = "#ffb300"
        else:
            confidence_label = "Low Confidence"
            confidence_color = "#ff1744"

    gauge_html = (
        f'<div class="custom-card">'
        f'  <div class="card-header">🛡️ Response Confidence</div>'
        f'  <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 10px 0;">'
        f'    <svg width="130" height="130" viewBox="0 0 120 120">'
        f'      <circle cx="60" cy="60" r="50" fill="none" stroke="#16242e" stroke-width="10" stroke-linecap="round" '
        f'              stroke-dasharray="{track_len:.1f} {circumference:.1f}" {rotation} />'
        f'      <circle cx="60" cy="60" r="50" fill="none" stroke="{confidence_color}" stroke-width="10" stroke-linecap="round" '
        f'              stroke-dasharray="{progress_len:.1f} {circumference:.1f}" {rotation} />'
        f'      <text x="60" y="62" text-anchor="middle" font-size="24" fill="#ffffff" font-weight="700" font-family="\'Plus Jakarta Sans\', sans-serif">'
        f'        {confidence_pct if last_turn else "--"}%'
        f'      </text>'
        f'      <text x="60" y="80" text-anchor="middle" font-size="9" fill="#90a4ae" font-family="\'Plus Jakarta Sans\', sans-serif">'
        f'        confidence'
        f'      </text>'
        f'    </svg>'
        f'    <div style="margin-top: 10px; color: {confidence_color}; font-weight: bold; font-size: 0.95rem;">{confidence_label}</div>'
        f'    <div style="color: #90a4ae; font-size: 0.78rem; text-align: center; margin-top: 6px; line-height: 1.4;">'
        f'      {"The response is well supported by the retrieved documents." if confidence_val >= 0.5 else "This response is grounded, but check documents for details." if last_turn else "Ask a question to see semantic score diagnostics."}'
        f'    </div>'
        f'  </div>'
        f'</div>'
    )
    st.markdown(gauge_html, unsafe_allow_html=True)
