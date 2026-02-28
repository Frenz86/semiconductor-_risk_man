"""
_shared.py — Tab: render_risk_badge, render_switching_badge, render_geo_detail, render_mermaid
"""

import streamlit as st
import streamlit.components.v1 as components


def render_risk_badge(risk_level, score):
    """Renderizza un badge del rischio."""
    color_map = {
        'ALTO': 'risk-red',
        'MEDIO': 'risk-yellow',
        'BASSO': 'risk-green'
    }
    css_class = color_map.get(risk_level, 'risk-green')
    st.markdown(f"""
    <div class="{css_class}">
        <h3>{risk_level}</h3>
        <p>Score: {score}/100</p>
    </div>
    """, unsafe_allow_html=True)


def render_switching_badge(classification):
    """Renderizza un badge per la classificazione di switching."""
    css_class = f"switching-{classification.lower()}"
    st.markdown(f'<span class="{css_class}">{classification}</span>', unsafe_allow_html=True)


def render_geo_detail(geo_risk):
    """Renderizza i dettagli del rischio geografico frontend/backend."""
    frontend = geo_risk.get('frontend_country', 'N/A').title()
    backend = geo_risk.get('backend_country', 'N/A').title()
    f_level = geo_risk.get('frontend_level', 'N/A')
    b_level = geo_risk.get('backend_level', 'N/A')

    st.markdown(f"""
    <div class="geo-frontend">
        <strong>Frontend (Wafer Fab):</strong> {frontend} - {f_level}<br/>
        <small>{geo_risk.get('frontend_reason', '')}</small>
    </div>
    <div class="geo-backend">
        <strong>Backend (Assembly/Test):</strong> {backend} - {b_level}<br/>
        <small>{geo_risk.get('backend_reason', '')}</small>
    </div>
    """, unsafe_allow_html=True)


def render_mermaid(mermaid_code, height=600):
    """Renderizza un diagramma Mermaid in Streamlit."""
    components.html(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.0/dist/mermaid.min.js"></script>
        <style>
            body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; background: white; }}
            .mermaid {{ background: white; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="mermaid" style="background: white;">
{mermaid_code}
        </div>
        <script>
            mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
        </script>
    </body>
    </html>
    """, height=height, scrolling=True)


# =============================================================================
# TAB 1: ANALISI RAPIDA
# =============================================================================

