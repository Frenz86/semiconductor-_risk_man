"""
Moduli per i tab della Supply Chain Resilience Platform v3.0
Ogni funzione rappresenta una tab e contiene tutta la logica di visualizzazione.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from typing import List, Any, Dict

# Import moduli personalizzati
from risk_engine import calculate_component_risk
from geo_risk import get_technology_node_risk, generate_risk_map_data
from whatif_simulator import (
    simulate_disruption, 
    get_predefined_scenarios, 
    _is_component_affected as _check_affected,
    SCENARIO_TYPES
)
from dependency_graph import HAS_NETWORKX

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

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

def render_tab_analisi_rapida():
    """Tab 1: Analisi Rapida Part Number"""
    st.header("Analisi Rapida Part Number")

    col1, col2 = st.columns([3, 1])

    with col1:
        pn_input = st.text_input(
            "Inserisci Part Number",
            placeholder="es. STM32MP157CAC3",
            key="pn_single_input"
        ).strip()

    with col2:
        st.write("")
        st.write("")
        analyze_btn = st.button("Analizza", type="primary", use_container_width=True)

    if analyze_btn and pn_input:
        component_data = st.session_state.db.lookup_part_number(
            pn_input, st.session_state.current_client
        )

        if component_data:
            st.success(f"Part Number **{pn_input}** trovato nel database!")

            # Calcola rischio v3
            risk = calculate_component_risk(component_data, st.session_state.run_rate)

            # Dashboard principale
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                render_risk_badge(risk['risk_level'], risk['score'])

            with col2:
                st.metric("Man-Hours Mitigazione", f"{risk['man_hours']}h")

            with col3:
                st.metric("Fattori Rischio", len(risk['factors']))

            with col4:
                switching = risk.get('switching_cost', {})
                st.metric("Switching Cost", f"{switching.get('total_switching_hours', 0):.0f}h")
                render_switching_badge(switching.get('classification', 'N/A'))

            # Dettaglio Geo Risk Frontend/Backend
            st.subheader("Rischio Geopolitico Frontend/Backend")
            geo = risk.get('geo_risk', {})
            col1, col2, col3 = st.columns(3)

            with col1:
                render_geo_detail(geo)

            with col2:
                tech = risk.get('tech_node_risk', {})
                if tech.get('nm'):
                    st.markdown(f"**Technology Node:** {tech['nm']}nm")
                    st.markdown(f"**Rischio:** {tech['level']}")
                    st.markdown(f"*{tech['reason']}*")
                else:
                    st.info("Technology node non specificato")

            with col3:
                st.metric("Geo Score Composito", f"{geo.get('composite_score', 0):.1f}/25")
                st.markdown(f"Frontend: {geo.get('frontend_score', 0)}/25 (peso 60%)")
                st.markdown(f"Backend: {geo.get('backend_score', 0)}/15 (peso 40%)")

            # Dettaglio Switching Cost
            if switching.get('breakdown'):
                st.subheader("Dettaglio Costo di Switching")
                for item in switching['breakdown']:
                    st.markdown(f"- **{item['item']}**: {item['hours']:.0f} ore")
                st.markdown(f"**Totale: {switching.get('total_switching_hours', 0):.0f} ore - {switching.get('classification', 'N/A')}**")

            # Fattori e suggerimenti
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Fattori di Rischio")
                if risk['factors']:
                    for factor in risk['factors']:
                        st.markdown(f"- {factor}")
                else:
                    st.info("Nessun fattore di rischio significativo")

            with col2:
                st.subheader("Suggerimenti")
                if risk['suggestions']:
                    for suggestion in risk['suggestions']:
                        st.markdown(f"- {suggestion}")
                else:
                    st.info("Nessuna azione richiesta")

            # Dati componente
            with st.expander("Dati Componente Completi"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Fornitore:** {component_data.get('Supplier Name', 'N/A')}")
                    st.markdown(f"**Categoria:** {component_data.get('Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)', 'N/A')}")
                    st.markdown(f"**Lead Time:** {component_data.get('Supplier Lead Time (weeks)', 'N/A')} settimane")
                    st.markdown(f"**Prezzo:** ${component_data.get('Unit Price ($)', 'N/A')}")
                with col2:
                    countries = [c for c in [
                        component_data.get('Country of Manufacturing Plant 1'),
                        component_data.get('Country of Manufacturing Plant 2'),
                        component_data.get('Country of Manufacturing Plant 3'),
                        component_data.get('Country of Manufacturing Plant 4')
                    ] if c and str(c).strip()]
                    st.markdown(f"**Paesi Produzione:** {', '.join(str(c) for c in countries) if countries else 'N/A'}")
                    st.markdown(f"**Proprietario:** {component_data.get('Proprietary (Y/N)**', 'N/A')}")
                    st.markdown(f"**Commodity:** {component_data.get('Commodity (Y/N)*', 'N/A')}")
                    st.markdown(f"**Stand-Alone:** {component_data.get('Stand-Alone Functional Device (Y/N)', 'N/A')}")

        else:
            st.error(f"Part Number **{pn_input}** non trovato nel database.")
            st.info("Puoi aggiungere questo part number nella tab 'Gestione Database'")

    elif not pn_input:
        st.info("""
        **Inserisci un Part Number** per analizzare il rischio della supply chain.

        Il sistema calcolerà:
        - Rischio geopolitico frontend/backend
        - Technology node risk
        - Costo di switching (porting SW + qualifica + certificazione)
        - Buffer stock coverage
        - Dipendenze funzionali
        """)


# =============================================================================
# TAB 2: ANALISI MULTIPLA
# =============================================================================

def render_tab_analisi_multipla():
    """Tab 2: Analisi Multipla Part Numbers"""
    st.header("Analisi Multipla Part Numbers")

    col1, col2 = st.columns(2)

    # File BOM di esempio disponibili
    BOM_EXAMPLES = {
        "02_BOM_Automotive_ADAS_ECU_15": "02_BOM_Automotive_ADAS_ECU_15.xlsx",
        "03_BOM_Industrial_IoT_Gateway_12": "03_BOM_Industrial_IoT_Gateway_12.xlsx",
        "01_BOM_Input_Template_10": "01_BOM_Input_Template_10.xlsx",
    }

    with col1:
        st.subheader("Carica BOM di Esempio")

        selected_bom = st.selectbox(
            "Seleziona BOM",
            options=list(BOM_EXAMPLES.keys()),
            help="Seleziona una BOM di esempio da analizzare"
        )

        if st.button("Carica e Analizza BOM", type="primary"):
            bom_file = BOM_EXAMPLES[selected_bom]
            try:
                # Leggi il file Excel
                xl = pd.ExcelFile(bom_file)
                target_sheet = None
                for sheet in xl.sheet_names:
                    if sheet.upper() == 'INPUTS':
                        target_sheet = sheet
                        break
                if target_sheet is None:
                    target_sheet = xl.sheet_names[0]

                df_raw = pd.read_excel(xl, sheet_name=target_sheet, header=None)
                header_row = None
                for i, row in df_raw.iterrows():
                    row_str = ' '.join(str(v).lower() for v in row.values if pd.notna(v))
                    if 'supplier' in row_str and ('part' in row_str or 'name' in row_str):
                        header_row = i
                        break
                if header_row is not None:
                    df_uploaded = pd.read_excel(xl, sheet_name=target_sheet, header=header_row)
                    df_uploaded = df_uploaded.dropna(how='all')
                else:
                    df_uploaded = pd.read_excel(xl, sheet_name=target_sheet)

                # Trova colonna Part Number
                pn_col = None
                for col in df_uploaded.columns:
                    col_lower = str(col).lower()
                    if 'part' in col_lower and 'number' in col_lower:
                        pn_col = col
                        break
                    if col_lower in ('mpn', 'pn', 'part_number', 'partnumber'):
                        pn_col = col
                        break

                if pn_col:
                    pns = df_uploaded[pn_col].dropna().astype(str).tolist()
                    pns = [p for p in pns if p.strip() and p.strip().lower() not in ('nan', 'none', '')]
                    st.success(f"Caricati **{len(pns)}** part numbers da **{selected_bom}**")

                    batch = _run_batch_analysis(pns, st.session_state.current_client, st.session_state.run_rate)
                    st.session_state.batch_results = batch
                else:
                    st.error("Colonna 'Part Number' non trovata nel file.")
            except Exception as e:
                st.error(f"Errore nel caricamento del file: {str(e)}")

    with col2:
        st.subheader("Carica il Tuo File")
        uploaded_file = st.file_uploader(
            "Carica file con lista Part Numbers",
            type=['csv', 'xlsx', 'xls'],
            help="Il file deve avere una colonna 'Part Number'"
        )

        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_uploaded = pd.read_csv(uploaded_file)
                else:
                    xl = pd.ExcelFile(uploaded_file)
                    target_sheet = None
                    for sheet in xl.sheet_names:
                        if sheet.upper() == 'INPUTS':
                            target_sheet = sheet
                            break
                    if target_sheet is None:
                        target_sheet = xl.sheet_names[0]

                    df_raw = pd.read_excel(xl, sheet_name=target_sheet, header=None)
                    header_row = None
                    for i, row in df_raw.iterrows():
                        row_str = ' '.join(str(v).lower() for v in row.values if pd.notna(v))
                        if 'supplier' in row_str and ('part' in row_str or 'name' in row_str):
                            header_row = i
                            break
                    if header_row is not None:
                        df_uploaded = pd.read_excel(xl, sheet_name=target_sheet, header=header_row)
                        df_uploaded = df_uploaded.dropna(how='all')
                    else:
                        df_uploaded = pd.read_excel(xl, sheet_name=target_sheet)

                pn_col = None
                for col in df_uploaded.columns:
                    col_lower = str(col).lower()
                    if 'part' in col_lower and 'number' in col_lower:
                        pn_col = col
                        break
                    if col_lower in ('mpn', 'pn', 'part_number', 'partnumber'):
                        pn_col = col
                        break

                if pn_col:
                    pns = df_uploaded[pn_col].dropna().astype(str).tolist()
                    pns = [p for p in pns if p.strip() and p.strip().lower() not in ('nan', 'none', '')]
                    st.success(f"Trovati **{len(pns)}** part numbers nel file")

                    if st.button("Analizza File Upload", type="primary"):
                        batch = _run_batch_analysis(pns, st.session_state.current_client, st.session_state.run_rate)
                        st.session_state.batch_results = batch
                else:
                    st.error("Colonna 'Part Number' non trovata nel file. Colonne trovate: " +
                             ", ".join(str(c) for c in df_uploaded.columns[:10]))
            except Exception as e:
                st.error(f"Errore nel caricamento: {str(e)}")

    # Mostra risultati batch
    batch = st.session_state.batch_results
    if batch:
        st.markdown("---")
        st.success(f"Trovati **{batch['found_count']}** di **{batch['total_count']}** part numbers")

        # Dashboard metriche
        col1, col2, col3, col4, col5 = st.columns(5)

        risks = batch['components_risk']

        with col1:
            red_count = sum(1 for r in risks if r['color'] == 'RED')
            st.metric("Alto Rischio", red_count)

        with col2:
            yellow_count = sum(1 for r in risks if r['color'] == 'YELLOW')
            st.metric("Medio Rischio", yellow_count)

        with col3:
            green_count = sum(1 for r in risks if r['color'] == 'GREEN')
            st.metric("Basso Rischio", green_count)

        with col4:
            total_mh = sum(r['man_hours'] for r in risks)
            st.metric("Totale Man-Hours", f"{total_mh:,}h")

        with col5:
            spof_count = len(batch['bom_risk'].get('spofs', []))
            st.metric("Single Points of Failure", spof_count)

        # Grafici
        col1, col2 = st.columns(2)

        with col1:
            risk_counts = {
                'Alto (RED)': red_count,
                'Medio (YELLOW)': yellow_count,
                'Basso (GREEN)': green_count
            }
            fig_pie = px.pie(
                values=list(risk_counts.values()),
                names=list(risk_counts.keys()),
                color=list(risk_counts.keys()),
                color_discrete_map={
                    'Alto (RED)': '#ff4444',
                    'Medio (YELLOW)': '#ffbb33',
                    'Basso (GREEN)': '#00C851'
                },
                title="Distribuzione per Livello di Rischio"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            sw_counts = {'TRIVIALE': 0, 'MODERATO': 0, 'COMPLESSO': 0, 'CRITICO': 0}
            for r in risks:
                cls = r.get('switching_cost', {}).get('classification', 'TRIVIALE')
                sw_counts[cls] = sw_counts.get(cls, 0) + 1

            fig_sw = px.pie(
                values=list(sw_counts.values()),
                names=list(sw_counts.keys()),
                color=list(sw_counts.keys()),
                color_discrete_map={
                    'TRIVIALE': '#00C851',
                    'MODERATO': '#ffbb33',
                    'COMPLESSO': '#ff8800',
                    'CRITICO': '#ff4444'
                },
                title="Distribuzione Costi di Switching"
            )
            st.plotly_chart(fig_sw, use_container_width=True)

        # Dettaglio rischi per componente
        st.subheader("Dettaglio Rischi per Componente")

        for risk in sorted(risks, key=lambda x: x['score'], reverse=True):
            color_emoji = "🔴" if risk['color'] == 'RED' else "🟡" if risk['color'] == 'YELLOW' else "🟢"
            sw = risk.get('switching_cost', {})
            sw_class = sw.get('classification', 'N/A')

            with st.expander(
                f"{color_emoji} **{risk['part_number']}** | {risk['supplier']} | Score: {risk['score']} | Switching: {sw_class}",
                expanded=(risk['color'] == 'RED')
            ):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Fattori di Rischio:**")
                    if risk['factors']:
                        for factor in risk['factors']:
                            st.markdown(f"- {factor}")
                    else:
                        st.markdown("- Nessun fattore significativo")

                with col2:
                    st.markdown("**Suggerimenti:**")
                    if risk['suggestions']:
                        for suggestion in risk['suggestions']:
                            st.markdown(f"- {suggestion}")
                    else:
                        st.markdown("- Nessuna azione richiesta")

                with col3:
                    st.markdown("**Geo Risk Frontend/Backend:**")
                    geo = risk.get('geo_risk', {})
                    render_geo_detail(geo)
                    st.markdown(f"**Man-Hours:** {risk['man_hours']}h")
                    st.markdown(f"**Switching:** {sw.get('total_switching_hours', 0):.0f}h ({sw_class})")

        # PN non trovati
        if batch['not_found']:
            st.warning(f"**{len(batch['not_found'])}** part numbers non trovati: {', '.join(batch['not_found'])}")


# =============================================================================
# TAB 3: ALBERO DIPENDENZE
# =============================================================================

def render_tab_albero_dipendenze():
    """Tab 3: Albero di Correlazione Funzionale"""
    st.header("Albero di Correlazione Funzionale")
    st.markdown("""
    Questo modulo costruisce il grafo delle dipendenze tra i componenti nella BOM.
    Se un componente **non standalone** (es. PMIC) si blocca, il sistema propaga il rischio
    a tutti i componenti dipendenti (es. MPU), calcolando uno **score di resilienza di coppia**.
    """)

    if not HAS_NETWORKX:
        st.error("Libreria `networkx` non installata. Esegui: `pip install networkx`")
    else:
        import networkx as nx
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')

        batch = st.session_state.batch_results
        if batch:
            bom_risk = batch['bom_risk']
            graph = bom_risk.get('dependency_graph', None)

            if graph is not None and isinstance(graph, nx.DiGraph) and len(graph.nodes()) > 0:

                # --- Visualizzazione networkx DiGraph ---
                st.subheader("Grafo Dipendenze (networkx DiGraph)")

                fig, ax = plt.subplots(figsize=(12, 7))

                # Layout gerarchico se possibile, altrimenti spring
                try:
                    # Prova layout a livelli (top-down)
                    pos = nx.shell_layout(graph)
                    if nx.is_directed_acyclic_graph(graph):
                        # Per DAG usa layout multipartite basato sulla profondita'
                        for node in graph.nodes():
                            try:
                                depth = nx.shortest_path_length(graph, node, list(nx.descendants(graph, node))[-1]) if nx.descendants(graph, node) else 0
                            except (nx.NetworkXError, IndexError):
                                depth = 0
                            graph.nodes[node]['layer'] = depth
                        pos = nx.multipartite_layout(graph, subset_key='layer')
                except Exception:
                    pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)

                # Colori nodi per livello di rischio
                chain_risks = bom_risk.get('chain_risks', {})
                node_colors = []
                for node in graph.nodes():
                    cr = chain_risks.get(node, {})
                    cc = cr.get('chain_color', graph.nodes[node].get('risk_color', 'GREEN'))
                    if cc == 'RED':
                        node_colors.append('#ff4444')
                    elif cc == 'YELLOW':
                        node_colors.append('#ffbb33')
                    else:
                        node_colors.append('#00C851')

                # Dimensione nodi proporzionale ai dipendenti
                node_sizes = []
                for node in graph.nodes():
                    try:
                        n_dep = len(list(nx.ancestors(graph, node)))
                    except nx.NetworkXError:
                        n_dep = 0
                    node_sizes.append(1500 + n_dep * 500)

                # Labels abbreviate
                labels = {}
                for node in graph.nodes():
                    supplier = graph.nodes[node].get('supplier', '')
                    label = node
                    if supplier and supplier != 'N/A':
                        label += f"\n({supplier})"
                    labels[node] = label

                # Disegna grafo
                nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=node_colors,
                                       node_size=node_sizes, edgecolors='#333', linewidths=2, alpha=0.9)
                nx.draw_networkx_labels(graph, pos, ax=ax, labels=labels,
                                        font_size=7, font_weight='bold')
                nx.draw_networkx_edges(graph, pos, ax=ax, edge_color='#1a3e6e',
                                       arrows=True, arrowsize=30, arrowstyle='-|>',
                                       connectionstyle='arc3,rad=0.1', width=2.5,
                                       min_source_margin=25, min_target_margin=25)

                # Etichette sugli archi
                edge_labels = {}
                for u, v, data in graph.edges(data=True):
                    edge_labels[(u, v)] = 'dipende da'
                nx.draw_networkx_edge_labels(graph, pos, ax=ax, edge_labels=edge_labels,
                                              font_size=6, font_color='#1a3e6e',
                                              label_pos=0.5, rotate=True)

                # Legenda
                from matplotlib.lines import Line2D
                from matplotlib.patches import FancyArrowPatch
                legend_elements = [
                    Line2D([0], [0], marker='o', color='w', markerfacecolor='#ff4444', markersize=12, label='Rischio ALTO'),
                    Line2D([0], [0], marker='o', color='w', markerfacecolor='#ffbb33', markersize=12, label='Rischio MEDIO'),
                    Line2D([0], [0], marker='o', color='w', markerfacecolor='#00C851', markersize=12, label='Rischio BASSO'),
                    Line2D([0], [0], color='#1a3e6e', linewidth=2.5, label='Dipendenza (A -> B)'),
                ]
                ax.legend(handles=legend_elements, loc='upper left', framealpha=0.9, fontsize=9)

                ax.set_title("Dependency Graph - Supply Chain BOM", fontsize=14, fontweight='bold')
                ax.axis('off')
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

                # --- Single Points of Failure ---
                spofs = bom_risk.get('spofs', [])
                if spofs:
                    st.subheader("Single Points of Failure")
                    st.markdown("Componenti la cui indisponibilita' blocca altri componenti:")

                    for spof in spofs:
                        st.markdown(f"""
                        <div style="background:#fff3cd; padding:10px; border-radius:5px; margin:5px 0; border-left: 4px solid #ff4444;">
                            <strong><span class="spof-badge">SPOF</span> {spof['part_number']}</strong> ({spof['supplier']}) -
                            {spof['category']}<br/>
                            <em>{spof['impact']}</em>
                        </div>
                        """, unsafe_allow_html=True)

                # --- Chain Risk Details ---
                chain_risks_data = bom_risk.get('chain_risks', {})
                if chain_risks_data:
                    st.subheader("Rischio di Catena per Componente")

                    chain_data = []
                    for pn, chain in chain_risks_data.items():
                        chain_data.append({
                            'Part Number': pn,
                            'Score Individuale': chain.get('own_score', 0),
                            'Score Catena': chain.get('chain_score', 0),
                            'Livello Catena': chain.get('chain_level', 'N/A'),
                            'Standalone': 'Si' if chain.get('is_standalone') else 'No',
                            'Dipende da': ', '.join(chain.get('dependencies', [])) or '-',
                            'Dipendono da questo': ', '.join(chain.get('dependents', [])) or '-',
                        })

                    if chain_data:
                        df_chain = pd.DataFrame(chain_data)
                        df_chain = df_chain.sort_values('Score Catena', ascending=False)
                        st.dataframe(df_chain, use_container_width=True, hide_index=True)

                    # Rischi di coppia
                    pair_risks = []
                    for pn, chain in chain_risks_data.items():
                        for pair in chain.get('pair_risks', []):
                            pair_risks.append(pair)

                    if pair_risks:
                        st.subheader("Score di Resilienza per Coppia Funzionale")
                        for pair in pair_risks:
                            emoji = "🔴" if pair['pair_color'] == 'RED' else "🟡" if pair['pair_color'] == 'YELLOW' else "🟢"
                            st.markdown(f"{emoji} **{pair['from']}** <- {pair['to']} : Score coppia = **{pair['pair_score']}**")
            else:
                st.info("Nessuna dipendenza trovata tra i componenti analizzati. Tutti i componenti sono standalone.")
        else:
            st.info("Esegui prima un'**Analisi Multipla** (Tab 2) per visualizzare le dipendenze tra componenti.")


# =============================================================================
# TAB 4: MAPPA GEOPOLITICA
# =============================================================================

def render_tab_mappa_geopolitica():
    """Tab 4: Mappa Rischio Geopolitico Frontend/Backend"""
    st.header("Mappa Rischio Geopolitico Frontend/Backend")
    st.markdown("""
    Questa mappa mostra la distribuzione geografica degli stabilimenti di fabbricazione
    distinguendo tra **Frontend** (fabbricazione wafer) e **Backend** (assemblaggio/test OSAT).
    """)

    batch = st.session_state.batch_results
    if batch:
        components_data = batch['components_data']
        components_risk = batch['components_risk']

        # Mappa con Folium
        try:
            import folium
            from streamlit_folium import st_folium

            markers = generate_risk_map_data(components_data)

            if markers:
                m = folium.Map(location=[30, 0], zoom_start=2, tiles='CartoDB positron')

                for marker in markers:
                    color = 'red' if marker['risk_score'] >= 20 else 'orange' if marker['risk_score'] >= 10 else 'green'
                    icon = 'industry' if marker['type'] == 'frontend' else 'cog'

                    popup_html = f"""
                    <b>{marker['label']}</b><br/>
                    Tipo: {'Frontend (Wafer Fab)' if marker['type'] == 'frontend' else 'Backend (Assembly/Test)'}<br/>
                    Paese: {marker['country']}<br/>
                    Rischio: {marker['risk_level']} ({marker['risk_score']}/25)
                    """

                    folium.Marker(
                        location=[marker['lat'], marker['lon']],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=marker['label'],
                        icon=folium.Icon(color=color, icon=icon, prefix='fa')
                    ).add_to(m)

                st_folium(m, width=None, height=500)
            else:
                st.info("Nessun dato geografico disponibile per la mappatura")
        except ImportError:
            st.warning("Librerie `folium` e `streamlit-folium` necessarie per la mappa. Esegui: `pip install folium streamlit-folium`")

        # Tabella rischio per regione
        st.subheader("Analisi Rischio per Regione")

        geo_table = []
        for i, risk in enumerate(components_risk):
            geo = risk.get('geo_risk', {})
            tech = risk.get('tech_node_risk', {})
            geo_table.append({
                'Part Number': risk.get('part_number', 'N/A'),
                'Fornitore': risk.get('supplier', 'N/A'),
                'Frontend': geo.get('frontend_country', 'N/A').title(),
                'Frontend Risk': geo.get('frontend_level', 'N/A'),
                'Backend': geo.get('backend_country', 'N/A').title(),
                'Backend Risk': geo.get('backend_level', 'N/A'),
                'Tech Node': f"{tech.get('nm', 'N/A')}nm" if tech.get('nm') else 'N/A',
                'Tech Risk': tech.get('level', 'N/A'),
                'Geo Score': geo.get('composite_score', 0),
            })

        if geo_table:
            df_geo = pd.DataFrame(geo_table)
            df_geo = df_geo.sort_values('Geo Score', ascending=False)
            st.dataframe(df_geo, use_container_width=True, hide_index=True)

            # Grafico a barre
            fig_geo = go.Figure()
            colors = ['#ff4444' if row['Geo Score'] >= 20 else '#ffbb33' if row['Geo Score'] >= 12 else '#00C851'
                      for _, row in df_geo.iterrows()]

            fig_geo.add_trace(go.Bar(
                x=df_geo['Part Number'],
                y=df_geo['Geo Score'],
                marker_color=colors,
                text=df_geo['Geo Score'].round(1),
                textposition='auto'
            ))
            fig_geo.update_layout(
                title="Geo Risk Score per Componente (Frontend/Backend Composito)",
                xaxis_title="Componente",
                yaxis_title="Geo Score",
                showlegend=False
            )
            fig_geo.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="CRITICO")
            fig_geo.add_hline(y=12, line_dash="dash", line_color="orange", annotation_text="ALTO")
            st.plotly_chart(fig_geo, use_container_width=True)
    else:
        st.info("Esegui prima un'**Analisi Multipla** (Tab 2) per visualizzare la mappa geopolitica.")


# =============================================================================
# TAB 5: COSTI DI SWITCHING
# =============================================================================

def render_tab_costi_switching():
    """Tab 5: Analisi Costi di Switching"""
    st.header("Analisi Costi di Switching")
    st.markdown("""
    Stima del costo temporale (ore-uomo) per sostituire ogni componente, basato su:
    - **SW Porting**: dimensione codice x complessita' OS (Baremetal/RTOS/Linux)
    - **Qualifica**: settimane di qualifica x 40 ore/settimana
    - **Certificazione**: moltiplicatore per tipo certificazione (AEC-Q100, MIL-STD, etc.)
    """)

    batch = st.session_state.batch_results
    if batch:
        components_risk = batch['components_risk']

        # Tabella principale
        sw_table = []
        for risk in components_risk:
            sw = risk.get('switching_cost', {})
            sw_table.append({
                'Part Number': risk.get('part_number', 'N/A'),
                'Fornitore': risk.get('supplier', 'N/A'),
                'Categoria': risk.get('category', 'N/A'),
                'OS': sw.get('os_type', 'N/A'),
                'SW Size (KB)': sw.get('sw_size_kb', 0),
                'Porting (h)': sw.get('sw_porting_hours', 0),
                'Qualifica (h)': sw.get('qualification_hours', 0),
                'Cert. Mult.': sw.get('certification_multiplier', 1.0),
                'Totale (h)': sw.get('total_switching_hours', 0),
                'Classificazione': sw.get('classification', 'N/A'),
            })

        df_sw = pd.DataFrame(sw_table)
        df_sw = df_sw.sort_values('Totale (h)', ascending=False)

        # Metriche riassuntive
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            critical = sum(1 for r in sw_table if r['Classificazione'] == 'CRITICO')
            st.metric("CRITICO", critical)
        with col2:
            complex_ = sum(1 for r in sw_table if r['Classificazione'] == 'COMPLESSO')
            st.metric("COMPLESSO", complex_)
        with col3:
            moderate = sum(1 for r in sw_table if r['Classificazione'] == 'MODERATO')
            st.metric("MODERATO", moderate)
        with col4:
            trivial = sum(1 for r in sw_table if r['Classificazione'] == 'TRIVIALE')
            st.metric("TRIVIALE", trivial)

        # Tabella
        st.dataframe(df_sw, use_container_width=True, hide_index=True)

        # Grafico a barre orizzontali
        fig_sw = go.Figure()

        color_map = {
            'TRIVIALE': '#00C851', 'MODERATO': '#ffbb33',
            'COMPLESSO': '#ff8800', 'CRITICO': '#ff4444'
        }
        colors = [color_map.get(row['Classificazione'], '#888') for _, row in df_sw.iterrows()]

        fig_sw.add_trace(go.Bar(
            y=df_sw['Part Number'],
            x=df_sw['Totale (h)'],
            orientation='h',
            marker_color=colors,
            text=[f"{h:.0f}h ({c})" for h, c in zip(df_sw['Totale (h)'], df_sw['Classificazione'])],
            textposition='auto'
        ))
        fig_sw.update_layout(
            title="Costo di Switching per Componente (ore-uomo)",
            xaxis_title="Ore-Uomo",
            yaxis_title="Componente",
            showlegend=False,
            height=max(300, len(df_sw) * 40 + 100),
        )
        fig_sw.add_vline(x=100, line_dash="dash", line_color="green", annotation_text="TRIVIALE")
        fig_sw.add_vline(x=500, line_dash="dash", line_color="orange", annotation_text="MODERATO")
        fig_sw.add_vline(x=2000, line_dash="dash", line_color="red", annotation_text="COMPLESSO")
        st.plotly_chart(fig_sw, use_container_width=True)

        # Dettaglio breakdown per componenti critici
        critical_components = [r for r in components_risk if r.get('switching_cost', {}).get('classification') in ('CRITICO', 'COMPLESSO')]
        if critical_components:
            st.subheader("Breakdown Componenti Critici/Complessi")
            for risk in critical_components:
                sw = risk.get('switching_cost', {})
                with st.expander(f"**{risk['part_number']}** - {sw.get('classification', 'N/A')} ({sw.get('total_switching_hours', 0):.0f}h)"):
                    for item in sw.get('breakdown', []):
                        st.markdown(f"- {item['item']}: **{item['hours']:.0f}h**")
                    st.markdown(f"**{sw.get('description', '')}**")
    else:
        st.info("Esegui prima un'**Analisi Multipla** (Tab 2) per visualizzare i costi di switching.")


# =============================================================================
# TAB 6: GESTIONE DATABASE
# =============================================================================

def render_tab_gestione_database():
    """Tab 6: Gestione Database Part Numbers"""
    st.header("Gestione Database Part Numbers")

    tab6_1, tab6_2, tab6_3 = st.tabs(["Statistiche", "Aggiungi Part Number", "Gestione Clienti"])

    with tab6_1:
        st.subheader("Statistiche Database")

        stats = st.session_state.db.get_stats()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Totale Part Numbers", stats['total_part_numbers'])
        with col2:
            st.metric("Totale Clienti", stats['total_clients'])
        with col3:
            st.metric("Record Cliente", stats['total_client_records'])

        st.markdown("---")

        if stats['categories']:
            st.subheader("Part Numbers per Categoria")
            df_cat = pd.DataFrame(list(stats['categories'].items()), columns=['Categoria', 'Count'])
            st.bar_chart(df_cat.set_index('Categoria'))

        if stats['suppliers']:
            st.subheader("Top Fornitori")
            df_sup = pd.DataFrame(list(stats['suppliers'].items()), columns=['Fornitore', 'Count']).head(10)
            st.dataframe(df_sup, use_container_width=True)

    with tab6_2:
        st.subheader("Aggiungi Nuovo Part Number")

        with st.form("add_new_pn_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_pn = st.text_input("Part Number *")
                new_supplier = st.text_input("Supplier Name *")
                new_category = st.selectbox(
                    "Category *",
                    ["MCU", "MPU", "Sensor", "Analogic", "Power", "Passive Component", "Transceiver Wireless"]
                )

            with col2:
                price = st.number_input("Unit Price ($)", min_value=0.0, value=0.0, step=0.01)
                lead_time = st.number_input("Lead Time (weeks) *", min_value=0, value=8)
                weeks_qualify = st.number_input("Weeks to Qualify", min_value=0, value=12)

            st.markdown("#### Paesi Produzione")
            col1, col2 = st.columns(2)
            with col1:
                country1 = st.text_input("Plant 1 Country *")
                country2 = st.text_input("Plant 2 Country")
            with col2:
                country3 = st.text_input("Plant 3 Country")
                country4 = st.text_input("Plant 4 Country")

            st.markdown("#### Geo Risk Frontend/Backend (v3.0)")
            col1, col2, col3 = st.columns(3)
            with col1:
                frontend_country = st.text_input("Frontend Country (wafer fab)")
                backend_country = st.text_input("Backend Country (assembly/test)")
            with col2:
                tech_node = st.text_input("Technology Node (es. 28nm, 180nm)")
            with col3:
                ems_used = st.selectbox("EMS Used", ["N", "Y"])
                ems_name = st.text_input("EMS Name (se usato)")

            st.markdown("#### SW/Firmware (v3.0)")
            col1, col2, col3 = st.columns(3)
            with col1:
                sw_size = st.number_input("SW Code Size (KB)", min_value=0, value=0)
            with col2:
                os_type = st.selectbox("OS Type", ["Baremetal", "RTOS", "FreeRTOS", "Linux", "Android"])
            with col3:
                memory_type = st.selectbox("Memory Type", ["Embedded", "External"])

            st.markdown("#### Caratteristiche")
            col1, col2, col3 = st.columns(3)
            with col1:
                proprietary = st.selectbox("Proprietary", ["N", "Y"])
            with col2:
                commodity = st.selectbox("Commodity", ["Y", "N"])
            with col3:
                standalone = st.selectbox("Stand-Alone", ["Y", "N"])

            st.markdown("#### Dati Cliente")
            col1, col2 = st.columns(2)
            with col1:
                qty_bom = st.number_input("Qty in BOM", min_value=1, value=1)
            with col2:
                buffer_stock = st.number_input("Buffer Stock Units", min_value=0, value=0)

            certification = st.text_input("Certification/Qualification (optional)")
            dependency = st.text_input("Dependencies (optional)")

            submitted = st.form_submit_button("Salva Part Number", type="primary")

            if submitted:
                if not new_pn or not new_supplier or not country1:
                    st.error("Part Number, Supplier Name e almeno un paese sono obbligatori")
                else:
                    new_pn_data = {
                        'Supplier Name': new_supplier,
                        'Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)': new_category,
                        'Country of Manufacturing Plant 1': country1,
                        'Country of Manufacturing Plant 2': country2 or '',
                        'Country of Manufacturing Plant 3': country3 or '',
                        'Country of Manufacturing Plant 4': country4 or '',
                        'Supplier Lead Time (weeks)': lead_time,
                        'Unit Price ($)': price,
                        'Weeks to qualify': weeks_qualify,
                        'Proprietary (Y/N)**': proprietary,
                        'Commodity (Y/N)*': commodity,
                        'Stand-Alone Functional Device (Y/N)': standalone,
                        'How Many Device of this specific PN are in the BOM?': qty_bom,
                        'If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units': buffer_stock,
                        'Specify Certification/Qualification': certification or '',
                        'In case answer on Column C is Y, Which other device in the BOM is necessary to run the PN on Column B? (e.g. PMIC for MPU, Memory for MPU)': dependency or '',
                        'Frontend_Country': frontend_country or '',
                        'Backend_Country': backend_country or '',
                        'Technology_Node': tech_node or '',
                        'SW_Code_Size_KB': sw_size,
                        'OS_Type': os_type,
                        'Memory_Type': memory_type,
                        'EMS_Used': ems_used,
                        'EMS_Name': ems_name or '',
                    }

                    if st.session_state.db.add_part_number(new_pn, new_pn_data, st.session_state.current_client):
                        st.success(f"Part Number **{new_pn}** salvato con successo!")
                    else:
                        st.error("Errore nel salvataggio")

        st.markdown("---")
        st.subheader("Ricerca Part Numbers")
        search_pattern = st.text_input("Cerca per pattern")
        if search_pattern:
            results = st.session_state.db.search_similar(search_pattern)
            if results:
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.info("Nessun risultato")

    with tab6_3:
        st.subheader("Gestione Clienti")

        clients = st.session_state.db.get_all_clients()
        if clients:
            st.dataframe(pd.DataFrame(clients), use_container_width=True)

        st.markdown("---")
        st.subheader("Aggiungi Nuovo Cliente")

        with st.form("add_client_form"):
            new_client_id = st.text_input("Client ID *")
            new_client_name = st.text_input("Client Name *")
            new_client_run_rate = st.number_input("Default Run Rate", min_value=1, value=5000)

            submitted = st.form_submit_button("Aggiungi Cliente", type="primary")

            if submitted:
                if not new_client_id or not new_client_name:
                    st.error("Client ID e Client Name sono obbligatori")
                elif st.session_state.db.add_client(new_client_id, new_client_name, new_client_run_rate):
                    st.success(f"Cliente **{new_client_name}** aggiunto con successo!")
                    st.rerun()
                else:
                    st.error("Errore nell'aggiunta del cliente")


# =============================================================================
# TAB 7: SIMULATORE WHAT-IF
# =============================================================================

COUNTRY_BLOCK_CONFIG = {
    'Taiwan': {'default_weeks': 8, 'risk_multiplier': 3.0},
    'China': {'default_weeks': 6, 'risk_multiplier': 2.5},
    'Korea': {'default_weeks': 4, 'risk_multiplier': 2.0},
    'Japan': {'default_weeks': 4, 'risk_multiplier': 1.8},
    'Malaysia': {'default_weeks': 3, 'risk_multiplier': 1.5},
    'Singapore': {'default_weeks': 3, 'risk_multiplier': 1.3},
    'Philippines': {'default_weeks': 3, 'risk_multiplier': 1.3},
}


def render_tab_simulatore_whatif():
    """Tab 7: Simulatore What-If - Scenari di Disruption"""
    st.header("Simulatore What-If - Scenari di Disruption")
    st.markdown("""
    Questo modulo permette di simulare l'impatto di scenari di disruption
    sulla supply chain e vedere come cambia il rischio.

    **Scenari supportati:**
    - Blocco geografico (es. Taiwan bloccata 4-8 settimane)
    - Aumento lead time (% su tutti i fornitori)
    - Interruzione fornitore specifico

    Il simulatore calcola:
    - Impatto su buffer stock (quando si esaurisce)
    - Variazione del rischio complessivo
    - Impatto finanziario stimato
    """)

    # -------------------------------------------------------------------------
    # VERIFICA DATI
    # -------------------------------------------------------------------------
    batch = st.session_state.batch_results

    if not batch:
        st.info("""
        Esegui prima un'**Analisi Multipla** (Tab 2) per caricare i dati della BOM.
        Il simulatore ha bisogno dei componenti e dei loro rischi calcolati.
        """)
    else:
        components_data = batch['components_data']
        components_risk = batch['components_risk']

        col1, col2 = st.columns([2, 1])

        # =====================================================================
        # COLONNA 1: CONFIGURAZIONE SCENARIO
        # =====================================================================
        with col1:
            st.subheader("Configurazione Scenario")

            scenario_option = st.radio(
                "Tipo di Scenario",
                options=["Predefinito", "Personalizzato"],
                horizontal=True,
                label_visibility="collapsed",
                key="scenario_option"
            )

            scenario_config = None

            # ------------------------- SCENARI PREDEFINITI --------------------
            if scenario_option == "Predefinito":
                predefined = get_predefined_scenarios()
                scenario_names = [s['name'] for s in predefined]

                selected_name = st.selectbox(
                    "Seleziona Scenario",
                    options=scenario_names,
                    help="Scegli tra gli scenari predefiniti",
                    key="predefined_select"
                )

                selected_scenario = next(
                    s for s in predefined if s['name'] == selected_name
                )

                if selected_scenario['type'] == 'country_block':
                    param_text = selected_scenario.get('country', '')
                elif selected_scenario['type'] == 'lead_time_increase':
                    param_text = f"{selected_scenario.get('increase_percent', 0)}%"
                elif selected_scenario['type'] == 'supplier_outage':
                    param_text = selected_scenario.get('supplier', '')
                else:
                    param_text = ""

                st.info(f"""
                **Scenario**: {selected_scenario['name']}
                - Tipo: {selected_scenario.get('type', '')}
                - Parametro: {param_text}
                - Durata: {selected_scenario['weeks']} settimane
                """)

                scenario_config = {
                    'type': selected_scenario.get('type', ''),
                    'description': selected_scenario.get(
                        'description',
                        selected_scenario.get('name', '')
                    ),
                    'weeks': selected_scenario.get('weeks', 0),
                }

                if selected_scenario['type'] == 'country_block':
                    scenario_config['country'] = selected_scenario.get('country', '')
                    scenario_config['risk_multiplier'] = selected_scenario.get('risk_multiplier', 2.0)
                elif selected_scenario['type'] == 'lead_time_increase':
                    scenario_config['increase_percent'] = selected_scenario.get('increase_percent', 50)
                    scenario_config['risk_multiplier'] = selected_scenario.get('risk_multiplier', 1.5)
                elif selected_scenario['type'] == 'supplier_outage':
                    scenario_config['supplier'] = selected_scenario.get('supplier', '')

                st.session_state.predefined_scenario = scenario_config

            # ------------------------ SCENARI PERSONALIZZATI -------------------
            else:
                st.write("**Configurazione Scenario Personalizzato**")

                def _apply_custom(form_data: Dict[str, Any]):
                    st.session_state.custom_scenario = form_data

                with st.form("custom_scenario_form"):
                    scenario_type_label = st.selectbox(
                        "Tipo Disruption",
                        options=list(SCENARIO_TYPES.values()),
                        help="Seleziona il tipo di scenario",
                        key="custom_type"
                    )

                    form_data: Dict[str, Any] = {}

                    if scenario_type_label == "Blocco Paese":
                        country = st.selectbox(
                            "Paese",
                            options=list(COUNTRY_BLOCK_CONFIG.keys()),
                            help="Seleziona il paese da simulare bloccato",
                            key="custom_country"
                        )
                        default_weeks = COUNTRY_BLOCK_CONFIG[country]['default_weeks']
                        risk_multiplier = COUNTRY_BLOCK_CONFIG[country]['risk_multiplier']

                        weeks = st.slider(
                            "Durata Blocco (settimane)",
                            min_value=1, max_value=52,
                            value=default_weeks, step=1,
                            key="custom_weeks_country"
                        )
                        form_data = {
                            'type': 'country_block',
                            'country': country,
                            'weeks': weeks,
                            'description': f"{country} bloccato per {weeks} settimane",
                            'risk_multiplier': risk_multiplier,
                        }

                    elif scenario_type_label == "Interruzione Fornitore":
                        suppliers_list = sorted(list(set(
                            str(c.get('Supplier Name', '')) for c in components_data
                        )))
                        supplier = st.selectbox(
                            "Fornitore",
                            options=suppliers_list,
                            help="Seleziona il fornitore da simulare interrotto",
                            key="custom_supplier"
                        )
                        weeks = st.slider(
                            "Durata Interruzione (settimane)",
                            min_value=1, max_value=52, value=4, step=1,
                            key="custom_weeks_supplier"
                        )
                        form_data = {
                            'type': 'supplier_outage',
                            'supplier': supplier,
                            'weeks': weeks,
                            'description': f"Fornitore {supplier} interrotto per {weeks} settimane",
                        }

                    elif scenario_type_label == "Aumento Lead Time":
                        increase_percent = st.slider(
                            "Aumento Lead Time (%)",
                            min_value=10, max_value=200, value=50, step=10,
                            key="custom_increase_percent"
                        )
                        weeks = st.slider(
                            "Durata Aumento (settimane)",
                            min_value=1, max_value=52, value=4, step=1,
                            key="custom_weeks_lead"
                        )
                        form_data = {
                            'type': 'lead_time_increase',
                            'increase_percent': increase_percent,
                            'weeks': weeks,
                            'description': f"Aumento lead time del {increase_percent}% per {weeks} settimane",
                            'risk_multiplier': 1.5,
                        }

                    st.form_submit_button(
                        "Applica",
                        type="primary",
                        on_click=_apply_custom,
                        args=(form_data,)
                    )

                scenario_config = st.session_state.get('custom_scenario', None)

        # =====================================================================
        # COLONNA 2: FILTRO COMPONENTI E AVVIO SIMULAZIONE
        # =====================================================================
        with col2:
            st.subheader("Componenti Specifici (Opzionale)")

            if scenario_config is not None and scenario_config.get('type'):
                scenario_type = scenario_config['type']

                if scenario_type == 'country_block':
                    country_filter = scenario_config.get('country', '')
                    st.info(f"Mostrando solo componenti con Frontend/Backend in **{country_filter}**")
                    filtered_indices = [
                        i for i, c in enumerate(components_data)
                        if _check_affected(c, scenario_config)
                    ]

                elif scenario_type == 'supplier_outage':
                    supplier_filter = scenario_config.get('supplier', '')
                    st.info(f"Mostrando solo componenti del fornitore **{supplier_filter}**")
                    filtered_indices = [
                        i for i, c in enumerate(components_data)
                        if _check_affected(c, scenario_config)
                    ]

                else:
                    filtered_indices = list(range(len(components_data)))
            else:
                filtered_indices = list(range(len(components_data)))

            if filtered_indices:
                component_names = [
                    components_data[i].get('Part Number', f'PN_{i}')
                    for i in filtered_indices
                ]
                selected_pn = st.selectbox(
                    "Componente Specifico (Analizza Tutti)",
                    options=["Analizza Tutti"] + component_names,
                    help="Seleziona un componente per vedere dettaglio",
                    key="component_select"
                )

                if selected_pn == "Analizza Tutti":
                    selected_indices = filtered_indices
                else:
                    idx_in_filtered = component_names.index(selected_pn)
                    selected_indices = [filtered_indices[idx_in_filtered]]
            else:
                st.info("Nessun componente affetto da questo scenario")
                selected_indices = []

            if st.button("Esegui Simulazione", type="primary", key="run_simulation"):
                if not scenario_config:
                    st.error("Per favore, configura uno scenario prima di eseguire la simulazione")
                elif not selected_indices:
                    st.warning("Seleziona almeno un componente da analizzare")
                else:
                    filtered_components = [components_data[i] for i in selected_indices]
                    filtered_risks = [components_risk[i] for i in selected_indices]

                    result = simulate_disruption(
                        filtered_components,
                        filtered_risks,
                        scenario_config,
                        st.session_state.run_rate
                    )
                    st.session_state.simulation_result = result

        # =====================================================================
        # RISULTATI
        # =====================================================================
        if 'simulation_result' in st.session_state:
            result = st.session_state.simulation_result
            summary = result['summary']
            scenario_info = result['scenario_info']

            st.markdown("---")
            st.subheader("Risultato Simulazione")

            col_result1, col_result2 = st.columns(2)

            with col_result1:
                st.markdown(f"""
                **Tipo**: {scenario_info['description']}
                **Durata**: {scenario_info['duration_weeks']} settimane
                **Parametro**: {scenario_info['parameter']}
                """)

                st.metric(
                    "Componenti Affetti",
                    f"{summary['affected_count']}/{summary['total_components']}"
                )
                st.metric("Componenti Critici", summary['critical_count'])

            with col_result2:
                delta = summary['score_change']
                delta_color = "normal" if delta == 0 else "inverse" if delta < 0 else "off"

                st.metric(
                    "Rischio Complessivo",
                    f"{summary['avg_adjusted_score']} ({summary['overall_level']})",
                    delta=delta,
                    delta_color=delta_color
                )

            st.markdown("### Impatto Finanziario")

            col_fin1, col_fin2, col_fin3 = st.columns(3)

            with col_fin1:
                st.metric(
                    "Valore BOM a Rischio",
                    f"${summary['total_bom_value']:,.2f}"
                )

            with col_fin2:
                weeks_lost = summary.get('total_production_lost_weeks', 0)
                st.metric(
                    "Produzione Persa",
                    f"{weeks_lost:.1f} settimane"
                )

            with col_fin3:
                revenue_loss = summary.get('total_financial_impact', 0)
                st.metric(
                    "Impatto Stimato",
                    f"${revenue_loss:,.2f}"
                )

            if result['impacted_components']:
                st.markdown("### Dettaglio Componenti Affetti")

                detail_rows = []
                for comp in result['impacted_components']:
                    detail_rows.append({
                        'Part Number': comp['part_number'],
                        'Fornitore': comp['supplier'],
                        'Score Orig.': comp['original_score'],
                        'Score Nuovo': comp['adjusted_score'],
                        'Variazione': comp['score_change'],
                        'Buffer Orig. (sett)': comp['original_buffer_weeks'],
                        'Buffer Nuovo (sett)': comp['remaining_buffer_weeks'],
                        'Sett. Perse': comp['weeks_lost'],
                        'Impatto $': comp['financial_impact'],
                    })

                df_detail = pd.DataFrame(detail_rows)
                df_detail = df_detail.sort_values('Impatto $', ascending=False)

                def color_score(val):
                    try:
                        v = float(val)
                    except Exception:
                        return ''
                    if v >= 55:
                        return 'background-color: #ff4444; color: white;'
                    elif v >= 30:
                        return 'background-color: #ffbb33; color: black;'
                    else:
                        return 'background-color: #00C851; color: white;'

                st.dataframe(
                    df_detail.style.applymap(
                        color_score,
                        subset=['Score Orig.', 'Score Nuovo']
                    ),
                    use_container_width=True,
                    hide_index=True
                )

            critical = result.get('critical_components', [])
            if critical:
                st.markdown("### Componenti Critici")
                st.warning("Questi componenti esauriscono il buffer durante la disruption:")

                for comp in critical[:10]:
                    depletion = comp['depletion_date'] or 'Immediato'
                    st.markdown(f"""
                    - **{comp['part_number']}** ({comp['supplier']})  
                      - Esaurisce: {depletion}  
                      - Sett. Rimanenti: {comp['remaining_buffer_weeks']:.1f}
                    """)

                if len(critical) > 10:
                    st.markdown(f"... e altri {len(critical) - 10} componenti")

            st.markdown("---")
            st.info("""
            **Nota**: Per vedere l'impatto su tutta la BOM, esegui una nuova **Analisi Multipla**
            con questo scenario applicato.
            """)


# =============================================================================
# TAB 8: GUIDA
# =============================================================================

def render_tab_guida():
    """Tab 8: Guida all'uso """

    st.markdown("""
    ## Architettura del Sistema        
    ### Importa BOM (Bill of Materials) da file Excel contenenti i componenti elettronici di un cliente
    ### Analizza i rischi dei componenti secondo molteplici dimensioni:
    - Rischi funzionali (dipendenze tra componenti)
    - Rischi geopolitici (localizzazione degli impianti di produzione)
    - Rischi di fornitura (single source, lead time, EOL, ecc.)
    - Costi di switching (complessità di sostituzione)
    ### Fornisce visualizzazioni per prendere decisioni:
    - Albero delle dipendenze per vedere catene critiche
    - Mappa geopolitica per rischi per regione
    - Dashboard con priorità di azione
    
    È uno strumento B2B per decision maker che devono valutare e mitigare i rischi nella catena di fornitura elettronica (es. aziende automotive, aerospaziali, consumer electronics).



    ### Modulo 1: Albero Dipendenze (Functional Chain Risk)
    - Costruisce un **grafo direzionale** delle dipendenze tra componenti
    - Identifica i **Single Points of Failure** (SPOF)
    - Propaga il rischio lungo le catene: se il PMIC e' ad alto rischio,
      anche l'MPU che ne dipende eredita quello score
    - Calcola **score di coppia**: max(risk_A, risk_B) per componenti collegati

    ### Modulo 2: Rischio Geopolitico Frontend/Backend
    - **Frontend** (60% del peso): dove viene fabbricato il wafer (es. TSMC Taiwan)
    - **Backend** (40% del peso): dove avviene assemblaggio/test (es. ASE Malaysia)
    - **Technology Node Risk**: nodi <= 7nm (CRITICO, solo TSMC/Samsung) fino a >= 130nm (BASSO)

    | Regione | Frontend Risk | Backend Risk |
    |---------|-------------|-------------|
    | Taiwan | CRITICO (25) | MEDIO (10) |
    | China | ALTO (20) | MEDIO-ALTO (12) |
    | Korea | MEDIO-ALTO (15) | MEDIO-BASSO (8) |
    | Malaysia | MEDIO (10) | ALTO (15) |
    | USA/EU | BASSO (3-5) | BASSO (2-3) |

    ### Modulo 3: Costi di Switching
    Stima le ore-uomo per sostituire un componente:

    | OS Type | Rate (ore/KB) | Esempio 2048KB |
    |---------|--------------|----------------|
    | Baremetal | 0.5 | 1,024h |
    | RTOS | 1.0 | 2,048h |
    | Linux | 2.0 | 4,096h |

    Moltiplicatori certificazione:
    - AEC-Q100 (automotive): x1.5
    - MIL-STD (military): x2.0
    - IEC 62443 (cybersecurity): x1.3

    Classificazione:
    - **TRIVIALE** (<100h): componente passivo, sostituzione diretta
    - **MODERATO** (100-500h): MCU semplice con baremetal
    - **COMPLESSO** (500-2000h): MCU con RTOS o componente con certificazioni
    - **CRITICO** (>2000h): MPU con Linux, equivale a redesign completo

    ### Fattori di Rischio (14 fattori, score capped a 100)

    | # | Fattore | Punti Max | Note |
    |---|---------|-----------|------|
    | 1 | Concentrazione Geografica | 25 | Frontend/Backend separati |
    | 2 | Single Source (stabilimenti) | 20 | Numero di plant produttivi |
    | 3 | Lead Time | 15 | Soglie 8/16/26 settimane |
    | 4 | Buffer Stock | 15 | Riduzione proporzionale se ampio |
    | 5 | Dipendenze | 10 | Chain risk propagation |
    | 6 | Proprietary/Commodity | 10 | Sostituibilita' del componente |
    | 7 | Certificazioni | 5 | Tempo di riqualifica |
    | 8 | **EOL Status** | **+15** | Active/NRND/Last_Buy/EOL/Obsolete |
    | 9 | **Alternative Sources** | **+10 / -3** | Fonti alternative sul mercato |
    | 10 | **Salute Finanziaria Fornitore** | **+8** | Rating A/B/C/D |
    | 11 | **Allocation Status** | **+10** | Normal/Constrained/Allocated |
    | 12 | **Aumento Prezzo** | **+5** | Ultimo aumento % come segnale di tensione |
    | 13 | **Package Type** | **+3** | Package avanzati (WLCSP, FCBGA...) |
    | 14 | **MTBF / Automotive Grade** | info | Informativi, non modificano lo score |
    | + | Technology Node | +5 | Nodi avanzati <= 7nm |
    | info | Switching Cost | n/a | Ore-uomo per sostituzione |

    ### Valori ammessi per i nuovi campi Excel

    | Campo | Valori | Esempio |
    |-------|--------|---------|
    | EOL_Status | Active, NRND, Last_Buy, EOL, Obsolete | Active |
    | Number_of_Alternative_Sources | 0, 1, 2, 3, ... | 2 |
    | Supplier_Financial_Health | A, B, C, D | A |
    | Allocation_Status | Normal, Constrained, Allocated | Normal |
    | Last_Price_Increase_Pct | Numero (%) | 15 |
    | Package_Type | QFP, BGA, WLCSP, QFN, SOP, DIP, CSP... | BGA |
    | Automotive_Grade | None, AEC-Q100, AEC-Q101, AEC-Q200 | AEC-Q100 |
    | MTBF_Hours | Numero (ore) | 100000 |

    ### Flusso di Lavoro Consigliato
    1. Seleziona il cliente dalla sidebar
    2. Vai su **Analisi Multipla** e inserisci i Part Numbers della BOM
    3. Analizza i risultati nei tab dedicati:
       - **Albero Dipendenze**: per capire le catene funzionali
       - **Mappa Geopolitica**: per visualizzare i rischi per regione
       - **Costi di Switching**: per prioritizzare le azioni di mitigazione
    """)

    st.markdown("---")
    st.subheader("Classificazione Finale")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="risk-red"><h3>ALTO</h3><p>Score >= 55</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="risk-yellow"><h3>MEDIO</h3><p>Score 30-54</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="risk-green"><h3>BASSO</h3><p>Score < 30</p></div>', unsafe_allow_html=True)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _run_batch_analysis(pns: List[str], client_id, run_rate):
    """Esegue analisi batch e restituisce risultati strutturati."""
    from risk_engine import calculate_bom_risk_v3
    
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
