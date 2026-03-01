"""
https://semiconductor-riskman.streamlit.app/

Supply Chain Risk Assessment Tool v4.1 - Resilience Platform

Per eseguire:
1. pip install -r requirements.txt
2. streamlit run app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import streamlit as st
from pn_lookup import PartNumberDatabase

# Import moduli UI
from tabs import (
    render_tab_analisi_multipla,
    render_tab_albero_dipendenze,
    render_tab_mappa_geopolitica,
    render_tab_tier2_visibility,
    render_tab_ip_dependencies,
    render_tab_costi_switching,
    render_tab_gestione_database,
    render_tab_simulatore_whatif,
    render_tab_dashboard_esecutiva,
    render_tab_guida,
    render_tab_filiera_commerciale,
)

# =============================================================================
# CONFIGURAZIONE PAGINA
# =============================================================================

st.set_page_config(
    page_title="Supply Chain Resilience Platform",
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
# LOGIN SYSTEM
# =============================================================================

# Credenziali hardcoded (in produzione usare un database o file sicuro)
USERS = {
    "admin": "admin",     # username: password
    "user": "admin",
    "guest": "guest"
}



def check_login(username, password):
    """Verifica le credenziali."""
    if username in USERS:
        # Per semplicità, confronto diretto (in produzione usare hash)
        return USERS[username] == password
    return False


def show_login_page():
    """Mostra la pagina di login."""
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }
        .login-title {
            color: #1976D2;
            font-size: 2rem;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="login-title">🔌 Supply Chain Platform</h1>', unsafe_allow_html=True)
    st.markdown("### Log in to continue")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        submit = st.form_submit_button("Login", use_container_width=True)

        if submit:
            if username and password:
                if check_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password!")
            else:
                st.warning("Please enter username and password.")

    st.markdown("---")
    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Inizializza lo stato della sessione."""
    # Verifica login
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if 'username' not in st.session_state:
        st.session_state.username = None

    # Se non loggato, mostra pagina login e termina
    if not st.session_state.logged_in:
        show_login_page()
        st.stop()

    if 'db' not in st.session_state:
        try:
            st.session_state.db = PartNumberDatabase()
            # Migra database se necessario
            st.session_state.db.migrate_database()
        except Exception as e:
            st.error(f"❌ Errore inizializzazione database: {str(e)}")
            st.info("📋 Contattare l'amministratore o verificare che 'data/part_numbers_db.xlsx' esista.")
            st.stop()

    if 'current_client' not in st.session_state:
        clients = st.session_state.db.get_all_clients()
        if clients:
            st.session_state.current_client = clients[0]['Client_ID']
        else:
            st.session_state.current_client = None

    if 'run_rate' not in st.session_state:
        client = st.session_state.db.get_client(st.session_state.current_client) if st.session_state.current_client else None
        st.session_state.run_rate = client['Default_Run_Rate'] if client else 5000

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


def save_run_rate_to_db():
    """Callback: salva il run rate nel database quando cambia."""
    if st.session_state.current_client:
        new_run_rate = st.session_state.run_rate_input
        success = st.session_state.db.update_client_run_rate(
            st.session_state.current_client,
            new_run_rate
        )
        if success:
            st.session_state.run_rate = new_run_rate



# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    # User info e logout
    st.markdown(f"👤 **User:** {st.session_state.username}")
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    st.markdown("---")
    st.header("Configuration")

    clients = st.session_state.db.get_all_clients()
    if clients:
        client_options = {f"{c['Client_Name']} ({c['Client_ID']})": c['Client_ID'] for c in clients}
        selected = st.selectbox(
            "Select Client",
            options=list(client_options.keys()),
            index=list(client_options.values()).index(st.session_state.current_client) if st.session_state.current_client else 0
        )
        st.session_state.current_client = client_options[selected]

        if st.session_state.run_rate != get_client_run_rate(st.session_state.current_client):
            st.session_state.run_rate = get_client_run_rate(st.session_state.current_client)
    else:
        st.warning("No clients found. Go to 'Database Management' to add one.")
        st.session_state.current_client = None

    st.session_state.run_rate = st.number_input(
        "Run Rate (PCB/week)",
        min_value=1,
        value=st.session_state.run_rate,
        step=100,
        key="run_rate_input",
        on_change=save_run_rate_to_db
    )

    st.markdown("---")
    st.header("Risk Legend")
    st.markdown('<div class="risk-red">HIGH (>=55 points)</div>', unsafe_allow_html=True)
    st.markdown('<div class="risk-yellow">MEDIUM (30-54 points)</div>', unsafe_allow_html=True)
    st.markdown('<div class="risk-green">LOW (<30 points)</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.header("Database Stats")
    stats = st.session_state.db.get_stats()
    st.metric("Part Numbers", stats['total_part_numbers'])
    st.metric("Clients", stats['total_clients'])

    st.markdown("---")
    st.header("Export")
    if st.session_state.get('batch_results'):
        from pdf_export import show_export_button

        show_export_button(
            st.session_state.batch_results,
            st.session_state.current_client,
            st.session_state.run_rate,
            key="export_sidebar"
        )
    else:
        st.info("Run a Multiple Analysis first")

# =============================================================================
# HEADER
# =============================================================================

st.title("Supply Chain Resilience Platform")
st.markdown("**Deterministic risk analysis with dependencies, geo-risk frontend/backend and switching costs**")

# =============================================================================
# TABS
# =============================================================================

tab_guida, tab_multipla, tab_dashboard, tab_albero, tab_mappa, tab_tier2, tab_ip, tab_switching, tab_filiera, tab_whatif, tab_database = st.tabs([
    "Guide",
    "Multiple Analysis",
    "Dashboard",
    "Dependency Tree",
    "Geopolitical Map",
    "Tier-2/3 Visibility",
    "IP/SW Dependencies",
    "Switching Costs",
    "Commercial Supply Chain",
    "What-If Simulator",
    "Database Management",
])

# =============================================================================
# RENDER TAB FUNCTIONS
# =============================================================================

with tab_guida:
    render_tab_guida()

with tab_multipla:
    render_tab_analisi_multipla()

with tab_dashboard:
    render_tab_dashboard_esecutiva()

with tab_albero:
    render_tab_albero_dipendenze()

with tab_mappa:
    render_tab_mappa_geopolitica()

with tab_tier2:
    render_tab_tier2_visibility()

with tab_ip:
    render_tab_ip_dependencies()

with tab_switching:
    render_tab_costi_switching()

with tab_filiera:
    render_tab_filiera_commerciale()

with tab_whatif:
    render_tab_simulatore_whatif()

with tab_database:
    render_tab_gestione_database()
