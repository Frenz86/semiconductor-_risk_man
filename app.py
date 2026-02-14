"""
Supply Chain Risk Assessment Tool v3.0 - Resilience Platform
=============================================================
Piattaforma per la valutazione proattiva del rischio e della resilienza
della supply chain elettronica.

Novità v3.0:
- Albero Dipendenze con grafo interattivo e chain risk propagation
- Mappa Geopolitica con rischio frontend/backend
- Costi di Switching con classificazione TRIVIALE/MODERATO/COMPLESSO/CRITICO
- Technology Node risk assessment
- Buffer stock con riduzione proporzionale del rischio

Per eseguire:
1. pip install -r requirements.txt
2. streamlit run app.py
"""

import streamlit as st
import streamlit.components.v1 as components
from risk_engine import calculate_component_risk, calculate_bom_risk, calculate_bom_risk_v3
from pn_lookup import PartNumberDatabase

# Import moduli UI
from tabs_modules import (
    render_tab_analisi_rapida,
    render_tab_analisi_multipla,
    render_tab_albero_dipendenze,
    render_tab_mappa_geopolitica,
    render_tab_costi_switching,
    render_tab_gestione_database,
    render_tab_simulatore_whatif,
    render_tab_guida
)

# =============================================================================
# CONFIGURAZIONE PAGINA
# =============================================================================

st.set_page_config(
    page_title="Supply Chain Resilience Platform v3.0",
    page_icon="🔌",
    layout="wide"
)

# =============================================================================
# CSS PERSONALIZZATO
# =============================================================================

st.markdown("""
<style>
    .risk-red { background-color: #ff4444; color: white; padding: 10px; border-radius: 5px; text-align: center; }
    .risk-yellow { background-color: #ffbb33; color: black; padding: 10px; border-radius: 5px; text-align: center; }
    .risk-green { background-color: #00C851; color: white; padding: 10px; border-radius: 5px; text-align: center; }
    .risk-orange { background-color: #ff8800; color: white; padding: 10px; border-radius: 5px; text-align: center; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin: 10px 0; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .pn-chip {
        display: inline-block;
        padding: 4px 12px;
        margin: 4px;
        border-radius: 16px;
        background-color: #e0e0e0;
        font-family: monospace;
        font-size: 0.9em;
    }
    .pn-found { background-color: #d4edda; color: #155724; }
    .pn-not-found { background-color: #f8d7da; color: #721c24; }
    .switching-triviale { background-color: #00C851; color: white; padding: 5px 10px; border-radius: 3px; display: inline-block; }
    .switching-moderato { background-color: #ffbb33; color: black; padding: 5px 10px; border-radius: 3px; display: inline-block; }
    .switching-complesso { background-color: #ff8800; color: white; padding: 5px 10px; border-radius: 3px; display: inline-block; }
    .switching-critico { background-color: #ff4444; color: white; padding: 5px 10px; border-radius: 3px; display: inline-block; }
    .spof-badge { background-color: #ff4444; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold; }
    .geo-frontend { border-left: 4px solid #1976D2; padding-left: 10px; margin: 5px 0; }
    .geo-backend { border-left: 4px solid #FF9800; padding-left: 10px; margin: 5px 0; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Inizializza lo stato della sessione."""
    if 'db' not in st.session_state:
        st.session_state.db = PartNumberDatabase()
        # Migra database se necessario
        st.session_state.db.migrate_database()

    if 'current_client' not in st.session_state:
        clients = st.session_state.db.get_all_clients()
        if clients:
            st.session_state.current_client = clients[0]['Client_ID']
        else:
            st.session_state.current_client = None

    if 'run_rate' not in st.session_state:
        client = st.session_state.db.get_client(st.session_state.current_client) if st.session_state.current_client else None
        st.session_state.run_rate = client['Default_Run_Rate'] if client else 5000

    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []

    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = None

init_session_state()

# =============================================================================
# FUNZIONI HELPER
# =============================================================================

def get_client_run_rate(client_id):
    """Ottiene il run rate di un cliente."""
    client = st.session_state.db.get_client(client_id)
    return client['Default_Run_Rate'] if client else 5000


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


def _is_component_affected(component: dict, scenario: dict) -> bool:
    """Verifica se un componente è affetto dallo scenario."""
    from whatif_simulator import _is_component_affected as _check_affected
    return _check_affected(component, scenario)


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


def run_batch_analysis(pns, client_id, run_rate):
    """Esegue analisi batch e restituisce risultati strutturati."""
    results = st.session_state.db.lookup_batch(pns, client_id)
    found_components = {pn: data for pn, data in results.items() if data is not None}
    not_found = [pn for pn, data in results.items() if data is None]

    if not found_components:
        return None

    # Calcola rischi individuali
    components_data = []
    components_risk = []
    for pn, data in found_components.items():
        risk = calculate_component_risk(data, run_rate)
        risk['part_number'] = pn
        risk['supplier'] = data.get('Supplier Name', 'N/A')
        risk['category'] = data.get('Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)', 'N/A')
        components_risk.append(risk)
        data['Part Number'] = pn
        components_data.append(data)

    # Calcola BOM risk v3 (con dependency graph)
    bom_risk_v3 = calculate_bom_risk_v3(components_data, components_risk)

    return {
        'components_data': components_data,
        'components_risk': components_risk,
        'bom_risk': bom_risk_v3,
        'found_count': len(found_components),
        'total_count': len(pns),
        'not_found': not_found,
    }


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.header("Configurazione")

    clients = st.session_state.db.get_all_clients()
    if clients:
        client_options = {f"{c['Client_Name']} ({c['Client_ID']})": c['Client_ID'] for c in clients}
        selected = st.selectbox(
            "Seleziona Cliente",
            options=list(client_options.keys()),
            index=list(client_options.values()).index(st.session_state.current_client) if st.session_state.current_client else 0
        )
        st.session_state.current_client = client_options[selected]

        if st.session_state.run_rate != get_client_run_rate(st.session_state.current_client):
            st.session_state.run_rate = get_client_run_rate(st.session_state.current_client)
    else:
        st.warning("Nessun cliente trovato. Vai su 'Gestione Database' per aggiungerne uno.")
        st.session_state.current_client = None

    st.session_state.run_rate = st.number_input(
        "Run Rate (PCB/settimana)",
        min_value=1,
        value=st.session_state.run_rate,
        step=100,
        key="run_rate_input"
    )

    st.markdown("---")
    st.header("Legenda Rischio")
    st.markdown('<div class="risk-red">ALTO (>=55 punti)</div>', unsafe_allow_html=True)
    st.markdown('<div class="risk-yellow">MEDIO (30-54 punti)</div>', unsafe_allow_html=True)
    st.markdown('<div class="risk-green">BASSO (<30 punti)</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.header("Database Stats")
    stats = st.session_state.db.get_stats()
    st.metric("Part Numbers", stats['total_part_numbers'])
    st.metric("Clienti", stats['total_clients'])

# =============================================================================
# HEADER
# =============================================================================

st.title("Supply Chain Resilience Platform v3.0")
st.markdown("**Analisi deterministica del rischio con dipendenze, geo-risk frontend/backend e costi di switching**")

# =============================================================================
# TABS
# =============================================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Analisi Rapida",
    "Analisi Multipla",
    "Albero Dipendenze",
    "Mappa Geopolitica",
    "Costi di Switching",
    "Gestione Database",
    "Simulatore What-If",
    "Guida"
])

# =============================================================================
# RENDER TAB FUNCTIONS
# =============================================================================

with tab1:
    render_tab_analisi_rapida()

with tab2:
    render_tab_analisi_multipla()

with tab3:
    render_tab_albero_dipendenze()

with tab4:
    render_tab_mappa_geopolitica()

with tab5:
    render_tab_costi_switching()

with tab6:
    render_tab_gestione_database()

with tab7:
    render_tab_simulatore_whatif()

with tab8:
    render_tab_guida()

# =============================================================================
# FOOTER
# =============================================================================

