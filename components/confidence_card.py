import streamlit as st

def render_confidence_card(last_turn: dict = None):
    """
    Renders a custom circular progress SVG widget in the right sidebar.
    """
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-header'>🛡️ Response Confidence</div>", unsafe_allow_html=True)
    
    confidence_val = last_turn.get("confidence", 0.0) if last_turn else 0.0
    confidence_pct = int(confidence_val * 100)
    
    # Dash array math (314 is circumference of circle with radius 50)
    dash_array = 314
    dash_offset = dash_array - (dash_array * confidence_val)
    
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
            
    gauge_html = f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 10px 0;">
        <svg width="120" height="120" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#16242e" stroke-width="8" />
            <circle cx="60" cy="60" r="50" fill="none" stroke="{confidence_color}" stroke-width="8" 
                    stroke-dasharray="{dash_array}" stroke-dashoffset="{dash_offset}" stroke-linecap="round" 
                    transform="rotate(-90 60 60)" />
            <text x="60" y="66" text-anchor="middle" font-size="20" fill="white" font-weight="700" font-family="'Plus Jakarta Sans', sans-serif">
                {confidence_pct if last_turn else "--"}%
            </text>
        </svg>
        <div style="margin-top: 15px; color: {confidence_color}; font-weight: bold; font-size: 0.95rem;">{confidence_label}</div>
        <div style="color: #90a4ae; font-size: 0.78rem; text-align: center; margin-top: 6px; line-height: 1.4;">
            { "The response is well supported by retrieved facts." if confidence_val >= 0.5 else "This response is grounded, but check documents for details." if last_turn else "Ask a question to see semantic score diagnostics." }
        </div>
    </div>
    """
    st.markdown(gauge_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
