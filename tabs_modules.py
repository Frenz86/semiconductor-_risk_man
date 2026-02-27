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
from pdf_export import show_export_button
from tier2_visibility import (
    calculate_tier2_risk,
    analyze_bom_tier2_bottlenecks,
    MATERIAL_DATABASE,
    CATEGORY_MATERIAL_MAPPINGS,
)
from ems_risk import analyze_bom_ems_risk
from distributor_risk import analyze_bom_distributor_risk, simulate_distributor_stockout

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

        # Pulsante export PDF
        st.subheader("📄 Esporta Report")
        show_export_button(batch, st.session_state.current_client, st.session_state.run_rate, key="export_tab_multipla")
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

def render_tab_tier2_visibility():
    """Tab: Visibilita' Tier-2/3 Supply Chain"""
    st.header("Visibilita' Tier-2/3 Supply Chain")
    st.markdown("""
    Analisi delle dipendenze a monte dei fornitori Tier-1: materiali critici
    (gas, wafer, chimici, substrati) e concentrazione geografica dei fornitori Tier-2/3.

    **Approccio ibrido**: mappature predefinite basate su categoria/nodo tecnologico
    + possibilita' di personalizzare con dati specifici.
    """)

    batch = st.session_state.get('batch_results')
    if not batch:
        st.info("Esegui prima un'**Analisi Multipla** per analizzare le dipendenze Tier-2/3.")
        return

    components_data = batch['components_data']
    components_risk = batch['components_risk']

    # Carica dati custom dal database
    db = st.session_state.db
    all_custom_materials = db.get_all_component_materials()

    # =========================================================================
    # SEZIONE 1: SOMMARIO BOTTLENECK BOM
    # =========================================================================
    st.subheader("Analisi Bottleneck a Livello BOM")

    bom_analysis = analyze_bom_tier2_bottlenecks(components_data, all_custom_materials)

    # KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Materiali Critici Unici", len(bom_analysis['top_bottlenecks']))
    with col2:
        st.metric("Score Tier-2 Medio", f"{bom_analysis['bom_tier2_score']:.1f}/25")
    with col3:
        country_conc = bom_analysis.get('country_concentration', {})
        if country_conc:
            top_country = max(country_conc, key=lambda c: country_conc[c]['total_exposure'])
            st.metric("Paese Piu' Esposto", top_country.title())
        else:
            st.metric("Paese Piu' Esposto", "N/A")
    with col4:
        high_t2 = sum(
            1 for r in components_risk
            if r.get('tier2_risk', {}).get('tier2_score', 0) > 15
        )
        st.metric("Componenti Alto Rischio T2", high_t2)

    # Tabella top bottlenecks
    if bom_analysis['top_bottlenecks']:
        bottleneck_rows = []
        for b in bom_analysis['top_bottlenecks'][:10]:
            bottleneck_rows.append({
                'Materiale': b['name'],
                'Categoria': b['category'],
                'Componenti Dipendenti': b['affected_count'],
                'Max Concentrazione': f"{b['max_concentration']:.0%}",
                'Paese Dominante': b['dominant_country'].title(),
                'Criticita\'': b['criticality'],
                'Sostituibilita\'': b['substitutability'],
            })
        st.dataframe(pd.DataFrame(bottleneck_rows), use_container_width=True, hide_index=True)

    # =========================================================================
    # SEZIONE 2: HEATMAP CONCENTRAZIONE PER PAESE
    # =========================================================================
    st.subheader("Heatmap Concentrazione Materiali per Paese")

    heatmap_data = bom_analysis.get('heatmap_data', [])
    if heatmap_data:
        df_heat = pd.DataFrame(heatmap_data)
        pivot = df_heat.pivot(index='Material', columns='Country', values='Exposure').fillna(0)

        if not pivot.empty:
            fig_heat = px.imshow(
                pivot,
                color_continuous_scale=['#e8f5e9', '#ffbb33', '#ff4444'],
                labels={'color': 'Esposizione'},
                title="Concentrazione Dipendenze Tier-2/3 per Paese",
                aspect='auto',
            )
            fig_heat.update_layout(height=max(400, len(pivot) * 30))
            st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Nessun dato per la heatmap.")

    # =========================================================================
    # SEZIONE 3: DETTAGLIO PER COMPONENTE
    # =========================================================================
    st.subheader("Dipendenze Tier-2 per Componente")

    comp_tier2 = bom_analysis.get('component_tier2_risks', {})

    for risk in sorted(
        components_risk,
        key=lambda x: x.get('tier2_risk', {}).get('tier2_score', 0),
        reverse=True
    ):
        pn = risk.get('part_number', 'N/A')
        tier2 = comp_tier2.get(pn, risk.get('tier2_risk', {}))
        tier2_score = tier2.get('tier2_score', 0)
        color_emoji = "🔴" if tier2_score > 15 else "🟡" if tier2_score > 8 else "🟢"

        custom_count = len(all_custom_materials.get(pn, []))
        custom_label = f" + {custom_count} custom" if custom_count > 0 else ""

        with st.expander(
            f"{color_emoji} **{pn}** | T2 Score: {tier2_score}/25 | "
            f"{len(tier2.get('materials', []))} materiali{custom_label}",
            expanded=(tier2_score > 15)
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Materiali Richiesti:**")
                for mat in tier2.get('materials', []):
                    conc_pct = mat.get('concentration_risk', 0) * 100
                    icon = "🔴" if conc_pct > 60 else "🟡" if conc_pct > 30 else "🟢"
                    custom_tag = " *(custom)*" if mat.get('is_custom_override') else ""
                    st.markdown(
                        f"- {icon} **{mat['name']}** - "
                        f"{mat.get('dominant_country', 'N/A').title()} ({conc_pct:.0f}%)"
                        f"{custom_tag}"
                    )

            with col2:
                if tier2.get('factors'):
                    st.markdown("**Fattori di Rischio:**")
                    for f in tier2['factors']:
                        st.markdown(f"- {f}")
                if tier2.get('suggestions'):
                    st.markdown("**Suggerimenti:**")
                    for s in tier2['suggestions']:
                        st.markdown(f"- {s}")

    # =========================================================================
    # SEZIONE 4: GESTIONE FORNITORI TIER-2 CUSTOM
    # =========================================================================
    st.markdown("---")
    st.subheader("Gestione Fornitori e Materiali Tier-2 Custom")

    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "Aggiungi Fornitore Tier-2",
        "Visualizza Fornitori",
        "Associa Materiale a PN"
    ])

    with sub_tab1:
        with st.form("add_tier2_supplier_form"):
            col1, col2 = st.columns(2)
            with col1:
                t2_name = st.text_input("Nome Fornitore Tier-2 *", key="t2_name")
                t2_material_type = st.text_input("Tipo Materiale *", key="t2_mat_type")
                material_keys_options = list(MATERIAL_DATABASE.keys()) + ["__custom__"]
                t2_material_key = st.selectbox(
                    "Material Key (predefinito o custom)",
                    options=material_keys_options,
                    key="t2_mat_key"
                )
            with col2:
                t2_country = st.text_input("Paese *", key="t2_country")
                t2_share = st.number_input("Market Share (%)", 0, 100, 10, key="t2_share")
                t2_criticality = st.selectbox(
                    "Criticita'",
                    ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                    key="t2_crit"
                )
                t2_substitutability = st.selectbox(
                    "Sostituibilita'",
                    ["HIGH", "MEDIUM", "LOW", "VERY_LOW"],
                    key="t2_subst"
                )

            t2_notes = st.text_area("Note", key="t2_notes")

            if st.form_submit_button("Salva Fornitore Tier-2", type="primary"):
                if t2_name and t2_material_type and t2_country:
                    success = db.add_tier2_supplier({
                        'Tier2_Supplier_Name': t2_name,
                        'Material_Type': t2_material_type,
                        'Material_Key': t2_material_key if t2_material_key != "__custom__" else t2_material_type.lower().replace(' ', '_'),
                        'Country': t2_country,
                        'Market_Share_Pct': t2_share,
                        'Criticality': t2_criticality,
                        'Substitutability': t2_substitutability,
                        'Notes': t2_notes,
                    })
                    if success:
                        st.success(f"Fornitore Tier-2 '{t2_name}' salvato con successo!")
                        st.rerun()
                    else:
                        st.error("Errore nel salvataggio.")
                else:
                    st.warning("Compila tutti i campi obbligatori (*).")

    with sub_tab2:
        suppliers = db.get_tier2_suppliers()
        if suppliers:
            df_suppliers = pd.DataFrame(suppliers)
            st.dataframe(df_suppliers, use_container_width=True, hide_index=True)

            # Rimozione fornitore
            supplier_ids = [s.get('Tier2_Supplier_ID', '') for s in suppliers]
            supplier_labels = [
                f"{s.get('Tier2_Supplier_ID', '')} - {s.get('Tier2_Supplier_Name', '')}"
                for s in suppliers
            ]
            selected_to_remove = st.selectbox(
                "Seleziona fornitore da rimuovere",
                options=supplier_labels,
                key="t2_remove_select"
            )
            if st.button("Rimuovi Fornitore", key="t2_remove_btn"):
                idx = supplier_labels.index(selected_to_remove)
                sid = supplier_ids[idx]
                if db.remove_tier2_supplier(sid):
                    st.success(f"Fornitore {sid} rimosso.")
                    st.rerun()
        else:
            st.info("Nessun fornitore Tier-2 custom nel database.")

    with sub_tab3:
        all_pns = db.get_all_part_numbers()
        if all_pns:
            with st.form("assign_material_form"):
                selected_pn = st.selectbox("Part Number", options=all_pns, key="assign_pn")
                material_keys_list = list(MATERIAL_DATABASE.keys())
                selected_material = st.selectbox(
                    "Materiale",
                    options=material_keys_list,
                    format_func=lambda k: f"{k} - {MATERIAL_DATABASE[k]['name']}",
                    key="assign_mat"
                )
                custom_concentration = st.slider(
                    "Concentrazione Custom (%)", 0, 100, 50, key="assign_conc"
                )
                custom_country = st.text_input(
                    "Paese Custom (override)", key="assign_country"
                )
                assign_notes = st.text_area("Note", key="assign_notes")

                if st.form_submit_button("Associa Materiale", type="primary"):
                    mat_info = MATERIAL_DATABASE.get(selected_material, {})
                    success = db.add_component_material(selected_pn, {
                        'Material_Key': selected_material,
                        'Material_Name': mat_info.get('name', selected_material),
                        'Custom_Concentration': custom_concentration / 100.0,
                        'Custom_Country': custom_country,
                        'Notes': assign_notes,
                    })
                    if success:
                        st.success(f"Materiale '{selected_material}' associato a {selected_pn}!")
                        st.rerun()
                    else:
                        st.error("Errore nell'associazione.")

            # Mostra associazioni esistenti
            st.markdown("---")
            st.markdown("**Associazioni esistenti:**")
            if all_custom_materials:
                rows = []
                for pn, mats in all_custom_materials.items():
                    for m in mats:
                        rows.append({
                            'Part Number': pn,
                            'Materiale': m.get('Material_Name', m.get('Material_Key', '')),
                            'Concentrazione': f"{float(m.get('Custom_Concentration', 0)) * 100:.0f}%"
                                if m.get('Custom_Concentration') else 'Default',
                            'Paese': m.get('Custom_Country', 'Default'),
                        })
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Nessuna associazione custom.")
            else:
                st.info("Nessuna associazione custom.")
        else:
            st.warning("Nessun Part Number nel database.")

    # =========================================================================
    # SEZIONE 5: RACCOMANDAZIONI DI MITIGAZIONE
    # =========================================================================
    st.markdown("---")
    st.subheader("Raccomandazioni di Mitigazione Tier-2/3")

    recommendations = bom_analysis.get('recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"{i}. {rec}")
    else:
        st.info("Nessuna raccomandazione specifica al momento.")


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
        # Pulsante export PDF
        st.subheader("📄 Esporta Report")
        show_export_button(batch, st.session_state.current_client, st.session_state.run_rate, key="export_tab_switching")
        st.markdown("---")
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
            yaxis={'categoryorder': 'total ascending'}
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

    tab6_1, tab6_2, tab6_3, tab6_ems, tab6_dist, tab6_alt, tab6_sup = st.tabs([
        "Statistiche", "Aggiungi Part Number", "Gestione Clienti",
        "EMS Providers", "Distributori", "Fonti Alternative", "Profili Fornitore"
    ])

    with tab6_1:
        st.subheader("Statistiche Database")

        stats = st.session_state.db.get_stats()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Part Numbers", stats['total_part_numbers'])
        with col2:
            st.metric("Clienti", stats['total_clients'])
        with col3:
            st.metric("EMS Providers", stats.get('total_ems_providers', 0))
        with col4:
            st.metric("Distributori", stats.get('total_distributors', 0))
        with col5:
            st.metric("Profili Fornitore", stats.get('total_supplier_profiles', 0))

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

    # -------------------------------------------------------------------------
    # SUB-TAB: EMS PROVIDERS (v4.0)
    # -------------------------------------------------------------------------
    with tab6_ems:
        st.subheader("EMS Providers")
        st.markdown("Gestisci i profili dei terzisti EMS (Foxconn, Jabil, Flextronics, ecc.)")

        existing_ems = st.session_state.db.get_all_ems_providers()
        if existing_ems:
            st.dataframe(pd.DataFrame(existing_ems), use_container_width=True)

            st.markdown("**Rimuovi EMS Provider:**")
            ems_ids = [e.get('EMS_ID', '') for e in existing_ems]
            ems_to_del = st.selectbox("Seleziona EMS da rimuovere", options=[''] + ems_ids, key="ems_del_sel")
            if ems_to_del and st.button("Rimuovi EMS", key="ems_del_btn"):
                if st.session_state.db.remove_ems_provider(ems_to_del):
                    st.success("EMS rimosso")
                    st.rerun()

        st.markdown("---")
        st.subheader("Aggiungi / Aggiorna EMS Provider")

        with st.form("add_ems_form"):
            col1, col2 = st.columns(2)
            with col1:
                ems_name_f = st.text_input("EMS Name *", placeholder="es. Foxconn, Jabil, Flex")
                ems_country_f = st.text_input("Country *", placeholder="es. China, Malaysia")
                ems_fin_f = st.selectbox("Financial Health", ["A", "B", "C", "D"])
            with col2:
                ems_cap_f = st.slider("Capacity Utilization (%)", 0, 100, 75)
                ems_backup_f = st.number_input("Backup Sites Count", min_value=0, value=0)
                ems_years_f = st.number_input("Years in Business", min_value=0, value=10)
            ems_certs_f = st.text_input("Certifications (comma-sep.)", placeholder="ISO9001, IATF16949, AS9100")
            ems_notes_f = st.text_area("Note", height=60)

            if st.form_submit_button("Salva EMS Provider", type="primary"):
                if not ems_name_f or not ems_country_f:
                    st.error("Nome e Paese sono obbligatori")
                else:
                    data = {
                        'EMS_Name': ems_name_f,
                        'Country': ems_country_f,
                        'Financial_Health': ems_fin_f,
                        'Capacity_Utilization_Pct': ems_cap_f,
                        'Backup_Sites_Count': ems_backup_f,
                        'Years_Business': ems_years_f,
                        'Certifications': ems_certs_f,
                        'Notes': ems_notes_f,
                    }
                    if st.session_state.db.add_ems_provider(data):
                        st.success(f"EMS Provider **{ems_name_f}** salvato!")
                        st.rerun()
                    else:
                        st.error("Errore nel salvataggio")

    # -------------------------------------------------------------------------
    # SUB-TAB: DISTRIBUTORI (v4.0)
    # -------------------------------------------------------------------------
    with tab6_dist:
        st.subheader("Distributori")
        st.markdown("Gestisci distributori (Arrow, Avnet, TTI, Digi-Key, ecc.) e le loro associazioni ai Part Numbers.")

        existing_dists = st.session_state.db.get_all_distributors()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Distributori registrati:**")
            if existing_dists:
                st.dataframe(pd.DataFrame(existing_dists)[[
                    'Distributor_ID', 'Name', 'Country', 'Financial_Health',
                    'Lead_Time_Markup_Weeks', 'Stock_Level_Weeks_Coverage'
                ]], use_container_width=True)
            else:
                st.info("Nessun distributore registrato")

        with col2:
            st.markdown("**Aggiungi / Aggiorna Distributore:**")
            with st.form("add_dist_form"):
                dist_name_f = st.text_input("Nome *", placeholder="es. Arrow Electronics")
                dist_country_f = st.text_input("Paese *", placeholder="es. USA")
                dist_fin_f = st.selectbox("Financial Health", ["A", "B", "C", "D"])
                dist_markup_f = st.number_input("Lead Time Markup (settimane)", min_value=0, value=2)
                dist_stock_f = st.number_input("Stock Coverage (settimane medie)", min_value=0.0, value=4.0, step=0.5)
                dist_certs_f = st.text_input("Certificazioni", placeholder="AS9120, ISO9001")
                dist_backup_f = st.number_input("Backup Distributors Count", min_value=0, value=0)
                dist_notes_f = st.text_area("Note", height=60)

                if st.form_submit_button("Salva Distributore", type="primary"):
                    if not dist_name_f or not dist_country_f:
                        st.error("Nome e Paese obbligatori")
                    else:
                        d = {
                            'Name': dist_name_f, 'Country': dist_country_f,
                            'Financial_Health': dist_fin_f,
                            'Lead_Time_Markup_Weeks': dist_markup_f,
                            'Stock_Level_Weeks_Coverage': dist_stock_f,
                            'Certifications': dist_certs_f,
                            'Backup_Count': dist_backup_f,
                            'Notes': dist_notes_f,
                        }
                        if st.session_state.db.add_distributor(d):
                            st.success(f"Distributore **{dist_name_f}** salvato!")
                            st.rerun()
                        else:
                            st.error("Errore nel salvataggio")

        st.markdown("---")
        st.subheader("Associa Distributore a Part Number")

        if existing_dists:
            with st.form("add_pn_dist_form"):
                col1, col2 = st.columns(2)
                with col1:
                    pn_for_dist = st.text_input("Part Number *")
                    dist_options = {f"{d['Name']} ({d['Distributor_ID']})": d['Distributor_ID'] for d in existing_dists}
                    sel_dist_label = st.selectbox("Distributore *", options=list(dist_options.keys()))
                with col2:
                    dist_priority = st.selectbox("Priority", ["Primary", "Secondary"])
                    dist_alloc_pct = st.slider("Allocation %", 0, 100, 100)

                if st.form_submit_button("Associa", type="primary"):
                    if not pn_for_dist:
                        st.error("Part Number obbligatorio")
                    else:
                        if st.session_state.db.add_part_distributor(pn_for_dist, {
                            'Distributor_ID': dist_options[sel_dist_label],
                            'Priority': dist_priority,
                            'Allocation_Pct': dist_alloc_pct,
                        }):
                            st.success(f"Associato {sel_dist_label} a {pn_for_dist}")
                        else:
                            st.error("Errore")
        else:
            st.info("Aggiungi prima un distributore per poterlo associare a un Part Number")

    # -------------------------------------------------------------------------
    # SUB-TAB: FONTI ALTERNATIVE (v4.0)
    # -------------------------------------------------------------------------
    with tab6_alt:
        st.subheader("Fonti Alternative (Multi-sourcing)")
        st.markdown("""
        Registra le fonti alternative per ogni Part Number, **includendo il paese di fabbricazione**.
        Il sistema rileverà automaticamente se tutte le alternative convergono sullo stesso paese
        (hidden single source).
        """)

        with st.form("add_alt_source_form"):
            col1, col2 = st.columns(2)
            with col1:
                alt_pn = st.text_input("Part Number *")
                alt_supplier = st.text_input("Supplier Name *", placeholder="es. Infineon")
                alt_frontend = st.text_input("Frontend Country *", placeholder="es. Taiwan")
                alt_backend = st.text_input("Backend Country", placeholder="es. Malaysia")
            with col2:
                alt_lt = st.number_input("Lead Time (settimane)", min_value=0, value=12)
                alt_fin = st.selectbox("Financial Health", ["A", "B", "C", "D"])
                alt_qual = st.selectbox("Qualification Status", ["Qualified", "In_Progress", "Not_Started"])
                alt_alloc = st.slider("Allocation %", 0, 100, 0)
            alt_notes = st.text_area("Note", height=60)

            if st.form_submit_button("Aggiungi Fonte Alternativa", type="primary"):
                if not alt_pn or not alt_supplier or not alt_frontend:
                    st.error("Part Number, Supplier e Frontend Country sono obbligatori")
                else:
                    d = {
                        'Supplier_Name': alt_supplier,
                        'Frontend_Country': alt_frontend,
                        'Backend_Country': alt_backend,
                        'Lead_Time_Weeks': alt_lt,
                        'Financial_Health': alt_fin,
                        'Qualification_Status': alt_qual,
                        'Allocation_Pct': alt_alloc,
                        'Notes': alt_notes,
                    }
                    if st.session_state.db.add_alt_source(alt_pn, d):
                        st.success(f"Fonte alternativa aggiunta per {alt_pn}")
                        st.rerun()
                    else:
                        st.error("Errore nel salvataggio")

        st.markdown("---")
        st.subheader("Fonti Alternative Registrate")
        all_alt = st.session_state.db.get_all_alt_sources()
        if all_alt:
            rows = []
            for pn, sources in all_alt.items():
                for s in sources:
                    rows.append({'Part Number': pn, **{k: v for k, v in s.items() if k != 'Part_Number'}})
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("Nessuna fonte alternativa registrata")

    # -------------------------------------------------------------------------
    # SUB-TAB: PROFILI FORNITORE (v4.0)
    # -------------------------------------------------------------------------
    with tab6_sup:
        st.subheader("Profili Fornitore (Tier1→Tier2 Linkage)")
        st.markdown("""
        Registra il profilo specifico di ogni fornitore Tier-1 con informazioni sul fab usato
        e le dipendenze materiali reali (invece dei default categoria+tech_node).

        Il campo **Key Materials Override** (JSON) permette di specificare dipendenze materiali
        personalizzate per questo fornitore. Esempio:
        `{"silicon_wafers": {"dominant_country": "japan", "concentration_risk": 0.60}}`
        """)

        existing_profiles = st.session_state.db.get_all_supplier_profiles()
        if existing_profiles:
            st.dataframe(pd.DataFrame(existing_profiles)[[
                'Supplier_Name', 'Primary_Fab', 'Primary_Fab_Country', 'Wafer_Source'
            ]], use_container_width=True)

        st.markdown("---")
        st.subheader("Aggiungi / Aggiorna Profilo Fornitore")

        with st.form("add_supplier_profile_form"):
            col1, col2 = st.columns(2)
            with col1:
                sp_name = st.text_input("Supplier Name *", placeholder="es. STMicroelectronics")
                sp_fab = st.text_input("Primary Fab", placeholder="es. TSMC Fab 18, Agrate")
                sp_fab_country = st.text_input("Primary Fab Country", placeholder="es. Italy, Taiwan")
            with col2:
                sp_wafer = st.text_input("Wafer Source", placeholder="es. Shin-Etsu (JP)")
                sp_notes = st.text_area("Note", height=60)
            sp_override = st.text_area(
                "Key Materials Override (JSON, opzionale)",
                height=80,
                placeholder='{"silicon_wafers": {"dominant_country": "japan", "concentration_risk": 0.55}}'
            )

            if st.form_submit_button("Salva Profilo Fornitore", type="primary"):
                if not sp_name:
                    st.error("Supplier Name obbligatorio")
                else:
                    d = {
                        'Supplier_Name': sp_name,
                        'Primary_Fab': sp_fab,
                        'Primary_Fab_Country': sp_fab_country,
                        'Wafer_Source': sp_wafer,
                        'Key_Materials_Override': sp_override,
                        'Notes': sp_notes,
                    }
                    if st.session_state.db.add_supplier_profile(d):
                        st.success(f"Profilo fornitore **{sp_name}** salvato!")
                        st.rerun()
                    else:
                        st.error("Errore nel salvataggio")


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

                    elif scenario_type_label == "Carenza Materiale Tier-2":
                        material_options = {v['name']: k for k, v in MATERIAL_DATABASE.items()}
                        selected_material_name = st.selectbox(
                            "Materiale",
                            options=list(material_options.keys()),
                            key="custom_material"
                        )
                        material_key = material_options[selected_material_name]

                        mat_info = MATERIAL_DATABASE[material_key]
                        countries = list(mat_info['primary_countries'].keys())
                        affected_countries = st.multiselect(
                            "Paesi Colpiti",
                            options=[c.title() for c in countries],
                            default=[c.title() for c in countries[:2]],
                            key="custom_material_countries"
                        )

                        weeks = st.slider(
                            "Durata Carenza (settimane)",
                            min_value=1, max_value=52, value=4, step=1,
                            key="custom_weeks_material"
                        )
                        form_data = {
                            'type': 'material_shortage',
                            'material_type': material_key,
                            'affected_countries': [c.lower() for c in affected_countries],
                            'weeks': weeks,
                            'description': f"Carenza {selected_material_name} per {weeks} settimane",
                            'risk_multiplier': 2.0,
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
# TAB 8: DASHBOARD ESECUTIVA
# =============================================================================

def render_tab_dashboard_esecutiva():
    """Tab 8: Dashboard Esecutiva - One-pager per il management"""
    st.header("📊 Dashboard Esecutiva")
    st.markdown("**One-pager con KPI principali per decisioni strategiche**")

    batch = st.session_state.batch_results
    if not batch:
        st.info("Esegui prima un'**Analisi Multipla** (Tab 2) per visualizzare la dashboard.")
        return

    components_data = batch['components_data']
    components_risk = batch['components_risk']
    bom_risk = batch['bom_risk']

    # =============================================================================
    # SEZIONE 1: KPI PRINCIPALI
    # =============================================================================
    st.subheader("KPI Principali")

    # Calcolo KPI
    risks = batch['components_risk']
    red_count = sum(1 for r in risks if r['color'] == 'RED')
    yellow_count = sum(1 for r in risks if r['color'] == 'YELLOW')
    green_count = sum(1 for r in risks if r['color'] == 'GREEN')

    avg_score = sum(r['score'] for r in risks) / len(risks) if risks else 0
    total_mh = sum(r['man_hours'] for r in risks)
    spof_count = len(bom_risk.get('spofs', []))

    # Valore BOM
    total_bom_value = bom_risk.get('total_bom_value', 0)

    # Componenti critici per categoria
    critical_by_category = {}
    for r in risks:
        cat = r.get('category', 'N/A')
        if r['color'] == 'RED':
            critical_by_category[cat] = critical_by_category.get(cat, 0) + 1

    # Top fornitori a rischio
    supplier_risk = {}
    for r in risks:
        supp = r.get('supplier', 'N/A')
        if supp not in supplier_risk:
            supplier_risk[supp] = {'total': 0, 'red': 0, 'count': 0}
        supplier_risk[supp]['total'] += r['score']
        supplier_risk[supp]['count'] += 1
        if r['color'] == 'RED':
            supplier_risk[supp]['red'] += 1

    # Media per fornitore
    for supp in supplier_risk:
        supplier_risk[supp]['avg'] = supplier_risk[supp]['total'] / supplier_risk[supp]['count']

    # Top 10 componenti a rischio
    top_risks = sorted(risks, key=lambda x: x['score'], reverse=True)[:10]

    # Heat map categorie x livello rischio
    category_risk_matrix = {}
    for r in risks:
        cat = r.get('category', 'N/A')
        level = r['risk_level']
        if cat not in category_risk_matrix:
            category_risk_matrix[cat] = {'ALTO': 0, 'MEDIO': 0, 'BASSO': 0, 'count': 0}
        category_risk_matrix[cat][level] += 1
        category_risk_matrix[cat]['count'] += 1

    # =============================================================================
    # DISPLAY KPI
    # =============================================================================
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6 = st.columns(6)

    with kpi_col1:
        st.metric("Rischio Medio", f"{avg_score:.1f}", delta="Basso" if avg_score < 30 else "Medio" if avg_score < 55 else "Alto")

    with kpi_col2:
        st.metric("Alto Rischio", red_count, delta=f"{red_count}/{len(risks)}")

    with kpi_col3:
        st.metric("Valore BOM", f"${total_bom_value:,.0f}")

    with kpi_col4:
        st.metric("Man-Hours Totali", f"{total_mh:,}h")

    with kpi_col5:
        st.metric("SPOF", spof_count)

    with kpi_col6:
        bom_level = bom_risk.get('risk_level', 'N/A')
        st.metric("Rischio BOM", bom_level)

    st.markdown("---")

    # =============================================================================
    # SEZIONE 2: GRAFICI PRINCIPALI
    # =============================================================================
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Pie chart distribuzione rischio
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
            title="Distribuzione Rischio",
            hole=0.4
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col2:
        # Bar chart fornitori a rischio
        if supplier_risk:
            supp_df = pd.DataFrame([
                {'Fornitore': s, 'Rischio Medio': d['avg'], 'Count': d['count'], 'Red': d['red']}
                for s, d in supplier_risk.items()
            ]).sort_values('Rischio Medio', ascending=False).head(10)

            colors = ['#ff4444' if r >= 55 else '#ffbb33' if r >= 30 else '#00C851' for r in supp_df['Rischio Medio']]
            fig_supp = px.bar(
                supp_df,
                x='Rischio Medio',
                y='Fornitore',
                orientation='h',
                color='Rischio Medio',
                color_continuous_scale=['#00C851', '#ffbb33', '#ff4444'],
                title="Top 10 Fornitori per Rischio Medio",
                text='Rischio Medio'
            )
            fig_supp.update_traces(texttemplate='%{text:.1f}', textposition='auto')
            fig_supp.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_supp, use_container_width=True)

    st.markdown("---")

    # =============================================================================
    # SEZIONE 3: HEAT MAP CATEGORIE x LIVELLO RISCHIO
    # =============================================================================
    st.subheader("🔥 Heat Map: Categorie x Livello Rischio")

    if category_risk_matrix:
        heatmap_data = []
        for cat, levels in category_risk_matrix.items():
            total = levels['count']
            heatmap_data.append({
                'Categoria': cat,
                'ALTO': levels['ALTO'],
                'MEDIO': levels['MEDIO'],
                'BASSO': levels['BASSO'],
                'Totale': total
            })

        df_heatmap = pd.DataFrame(heatmap_data).sort_values('Totale', ascending=False)

        # Visualizzazione tabellare con colori
        def highlight_risk(val, col):
            if col == 'Categoria' or col == 'Totale':
                return ''
            if val > 0:
                if col == 'ALTO':
                    return 'background-color: #ff4444; color: white; font-weight: bold;'
                elif col == 'MEDIO':
                    return 'background-color: #ffbb33; color: black;'
                else:
                    return 'background-color: #00C851; color: white;'
            return ''

        styled_df = df_heatmap.style.apply(
            lambda row: [highlight_risk(row[val], val) for val in row.index],
            axis=1
        )
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # =============================================================================
    # SEZIONE 4: TOP 10 RISCHI
    # =============================================================================
    st.subheader("🚨 Top 10 Componenti a Rischio")

    top10_data = []
    for i, r in enumerate(top_risks, 1):
        geo = r.get('geo_risk', {})
        sw = r.get('switching_cost', {})
        lead_time = r.get('lead_time_weeks', 0)

        # Trova lead time dal componente originale
        for comp in components_data:
            if comp.get('Part Number') == r.get('part_number'):
                lead_time = comp.get('Supplier Lead Time (weeks)', 0)
                break

        top10_data.append({
            'Rank': i,
            'Part Number': r.get('part_number', 'N/A'),
            'Fornitore': r.get('supplier', 'N/A'),
            'Score': r['score'],
            'Livello': r['risk_level'],
            'Lead Time (w)': lead_time,
            'Geo Score': geo.get('composite_score', 0),
            'Switching': sw.get('classification', 'N/A'),
            'SPOF': 'Sì' if any('solo stabilimento' in f.lower() for f in r['factors']) else 'No'
        })

    df_top10 = pd.DataFrame(top10_data)

    # Colora le righe per livello di rischio
    def color_row(row):
        if row['Livello'] == 'ALTO':
            return ['background-color: #ff444433'] * len(row)
        elif row['Livello'] == 'MEDIO':
            return ['background-color: #ffbb3333'] * len(row)
        return [''] * len(row)

    styled_top10 = df_top10.style.apply(color_row, axis=1)
    st.dataframe(styled_top10, use_container_width=True, hide_index=True)

    st.markdown("---")

    # =============================================================================
    # SEZIONE 4b: ALERT FILIERA COMMERCIALE (v4.0)
    # =============================================================================
    st.subheader("🔗 Alert Filiera Commerciale")

    # Hidden Single Source
    hidden_spof_list = [
        r for r in risks
        if r.get('hidden_single_source', {}).get('hidden_spof_score', 0) >= 4
    ]
    # Mono-distributore
    mono_dist_list = [
        r for r in risks
        if r.get('distributor_risk', {}).get('distributor_count', 1) == 1
           and r.get('distributor_risk', {}).get('has_distributors', True)
    ]
    # EMS single-site
    ems_spof_list = [
        r for r in risks
        if r.get('ems_risk', {}).get('ems_used') and r.get('ems_risk', {}).get('ems_score', 0) >= 12
    ]

    filiera_col1, filiera_col2, filiera_col3 = st.columns(3)

    with filiera_col1:
        if hidden_spof_list:
            st.error(f"**Hidden Single Source: {len(hidden_spof_list)} componenti**")
            st.markdown(
                "Questi componenti hanno fonti alternative ma condividono lo stesso paese di fab:"
            )
            for r in hidden_spof_list[:5]:
                hs = r.get('hidden_single_source', {})
                st.markdown(
                    f"- **{r.get('part_number')}** – {hs.get('overlap_country', '?').title()} "
                    f"({hs.get('overlap_count', 0)}/{hs.get('total_sources', 0)} fonti)"
                )
        else:
            st.success("Nessun Hidden Single Source rilevato")

    with filiera_col2:
        if mono_dist_list:
            st.warning(f"**Mono-Distributore: {len(mono_dist_list)} componenti**")
            for r in mono_dist_list[:5]:
                dist = r.get('distributor_risk', {})
                st.markdown(
                    f"- **{r.get('part_number')}** → {dist.get('primary_distributor', 'N/A')}"
                )
        else:
            st.success("Nessun componente mono-distributore")

    with filiera_col3:
        if ems_spof_list:
            st.warning(f"**EMS ad alto rischio: {len(ems_spof_list)} componenti**")
            for r in ems_spof_list[:5]:
                ems = r.get('ems_risk', {})
                st.markdown(
                    f"- **{r.get('part_number')}** – {ems.get('ems_name', 'N/A')} "
                    f"(score {ems.get('ems_score', 0)})"
                )
        else:
            st.success("Nessun EMS critico")

    st.markdown("---")

    # =============================================================================
    # SEZIONE 5: RIEPILOGO AZIONI RACCOMANDATE
    # =============================================================================
    st.subheader("✅ Azioni Raccomandate per Priorità")

    # Raggruppa suggerimenti per priorità
    urgent_actions = []
    high_priority_actions = []
    medium_priority_actions = []

    for r in risks:
        pn = r.get('part_number', 'N/A')
        supplier = r.get('supplier', 'N/A')
        score = r['score']

        for sugg in r.get('suggestions', []):
            action = f"**{pn}** ({supplier}, Score: {score}): {sugg}"

            if any(word in sugg.lower() for word in ['urgente', 'critical', 'immediatamente', 'last-time buy']):
                urgent_actions.append(action)
            elif any(word in sugg.lower() for word in ['qualificare', 'identificare', 'avviare', 'pianificare']):
                high_priority_actions.append(action)
            else:
                medium_priority_actions.append(action)

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        st.markdown("### 🔴 Urgenti")
        if urgent_actions:
            for action in urgent_actions[:5]:
                st.markdown(f"- {action}")
        else:
            st.info("Nessuna azione urgente")

    with action_col2:
        st.markdown("### 🟠 Alta Priorità")
        if high_priority_actions:
            for action in high_priority_actions[:5]:
                st.markdown(f"- {action}")
        else:
            st.info("Nessuna azione alta priorità")

    with action_col3:
        st.markdown("### 🟡 Media Priorità")
        if medium_priority_actions:
            for action in medium_priority_actions[:5]:
                st.markdown(f"- {action}")
        else:
            st.info("Nessuna azione media priorità")

    st.markdown("---")

    # =============================================================================
    # SEZIONE 6: TREND TEMPORE (simulato - base per futuro sviluppo)
    # =============================================================================
    st.subheader("📈 Trend Rischio nel Tempo")

    st.info("""
    **Nota**: Il trend storico richiede il salvataggio delle analisi nel tempo.
    Questa sezione mostrerà l'evoluzione del rischio della BOM nelle diverse versioni.

    *Per abilitare questa funzionalità, implementare il salvataggio storico delle analisi.*
    """)

    # Mostra solo la situazione corrente come baseline
    col_trend1, col_trend2, col_trend3 = st.columns(3)

    with col_trend1:
        st.markdown("**Baseline Attuale**")
        st.metric("Data", pd.Timestamp.now().strftime('%Y-%m-%d'))
        st.metric("Score Medio", f"{avg_score:.1f}")
        st.metric("Componenti Critici", red_count)

    with col_trend2:
        st.markdown("**Obiettivo -3 mesi**")
        target_reduction = avg_score * 0.85  # -15%
        st.metric("Target Score", f"{target_reduction:.1f}", "-15%")
        st.metric("Target Critici", max(0, red_count - red_count // 2))

    with col_trend3:
        st.markdown("**Obiettivo -6 mesi**")
        target_reduction_6m = avg_score * 0.7  # -30%
        st.metric("Target Score", f"{target_reduction_6m:.1f}", "-30%")
        st.metric("Target Critici", max(0, red_count * 2 // 3))

    st.markdown("---")

    # =============================================================================
    # SEZIONE 7: EXPORT
    # =============================================================================
    st.subheader("📄 Export Dashboard")

    show_export_button(batch, st.session_state.current_client, st.session_state.run_rate, key="export_dashboard")


# =============================================================================
# TAB 9: GUIDA
# =============================================================================

def render_tab_guida():
    """Tab Guida: documentazione completa della piattaforma v4.0"""

    st.title("Supply Chain Resilience Platform — v4.0")
    st.markdown(
        "Strumento B2B per la valutazione e mitigazione proattiva del rischio nella "
        "supply chain elettronica. Copre l'intera filiera verticale: dai materiali Tier-2 "
        "fino al canale distributivo."
    )

    st.markdown("---")

    # =========================================================================
    # ARCHITETTURA
    # =========================================================================
    st.header("Architettura della Piattaforma")

    st.markdown("""
La piattaforma modella **quattro livelli della supply chain** in modo integrato:

```
Materiali Tier-2/3          Neon gas, photoresists, wafer, terre rare, SiC...
        ↓
Fornitore Tier-1            STMicro, Infineon, NXP, TI, Renesas...
        ↓
EMS / Terzista              Foxconn, Flextronics, Jabil, produzione in house...
        ↓
Canale Distributivo         Arrow, Avnet, TTI, Digi-Key...
        ↓
Cliente (BOM)               Componenti elettronici in produzione
```

Il **risk engine deterministico** aggrega 18 fattori in uno score 0–100 per componente,
con cap a 100 e classificazione ALTO/MEDIO/BASSO.
    """)

    st.markdown("---")

    # =========================================================================
    # TAB DISPONIBILI
    # =========================================================================
    st.header("Tab della Piattaforma")

    tab_docs = {
        "Analisi Multipla": "Carica una BOM da file Excel (o seleziona un esempio) ed esegui l'analisi batch. "
                            "Tutti i tab successivi si popolano da qui. Supporta file .xlsx e .csv con colonna 'Part Number'.",
        "Dashboard Esecutiva": "One-pager per il management: KPI principali, heat map categorie × livello rischio, "
                               "top 10 componenti a rischio, alert filiera commerciale (hidden SPOF, mono-distributore, EMS critico), "
                               "azioni raccomandate per priorità.",
        "Albero Dipendenze": "Grafo direzionale delle dipendenze funzionali tra componenti. "
                             "Identifica SPOF, propaga il rischio lungo le catene, calcola score di coppia. "
                             "Richiede NetworkX (pip install networkx).",
        "Mappa Geopolitica": "Visualizza i rischi geopolitici Frontend (wafer fab) e Backend (assembly/test) "
                             "su mappa interattiva. Heatmap concentrazione paesi e analisi per fornitore.",
        "Tier-2/3 Visibility": "Analizza le dipendenze sui materiali critici a monte dei fornitori Tier-1 "
                               "(neon gas, photoresists, wafer, terre rare, SiC, palladio, ecc.). "
                               "Con profili fornitore registrati, usa dati fab-specifici invece dei default per categoria.",
        "Costi di Switching": "Stima le ore-uomo per sostituire un componente: porting SW, validazione, certificazione. "
                              "Classificazione TRIVIALE/MODERATO/COMPLESSO/CRITICO.",
        "Filiera Commerciale": "**Nuovo v4.0** — Analisi EMS risk, rischio distributore, hidden single source detection, "
                               "simulatore stock-out distributore.",
        "Simulatore What-If": "Simula 12 scenari predefiniti (blocco Taiwan, carenze materiali, stock-out distributore, "
                              "EMS overload, aumento lead time). Calcola impatto su buffer stock e impatto finanziario.",
        "Gestione Database": "CRUD completo per tutti i dati: part numbers, clienti, EMS providers, distributori, "
                             "fonti alternative, profili fornitore. Tutti i dati si inseriscono qui — mai modificando l'Excel manualmente.",
    }

    for tab_name, description in tab_docs.items():
        with st.expander(f"**{tab_name}**"):
            st.markdown(description)

    st.markdown("---")

    # =========================================================================
    # MODELLO DI SCORING — 18 FATTORI
    # =========================================================================
    st.header("Modello di Scoring — 18 Fattori")
    st.markdown("Score finale = somma fattori 1–18, capped a 100.")

    st.markdown("""
| # | Fattore | Max | Livello supply chain |
|---|---------|-----|----------------------|
| 1 | Concentrazione Geografica (Frontend/Backend) | 25 | Fornitore Tier-1 |
| 2 | Single Source (stabilimenti produttivi) | 20 | Fornitore Tier-1 |
| 3 | Lead Time | 15 | Fornitore Tier-1 |
| 4 | Buffer Stock | −15 (bonus riduzione) | Cliente |
| 5 | Dipendenze Funzionali (chain risk) | 10 | BOM |
| 6 | Proprietary / Commodity | 10 | Componente |
| 7 | Certificazioni richieste | 5 | Componente |
| 8 | EOL Status | +15 | Fornitore Tier-1 |
| 9 | Alternative Sources (n. fonti) | +10 / −3 | Mercato |
| 10 | Salute Finanziaria Fornitore | +8 | Fornitore Tier-1 |
| 11 | Allocation Status | +10 | Mercato |
| 12 | Aumento Prezzo (% ultimo ciclo) | +5 | Mercato |
| 13 | Package Type | +3 | Componente |
| 14 | Technology Node | +5 | Wafer fab |
| 15 | Tier-2/3 Supply Chain | +15 | Materiali Tier-2 |
| 16 | **EMS Risk** | **+12** | **EMS / Terzista** |
| 17 | **Distributor Risk** | **+10** | **Canale Distributivo** |
| 18 | **Hidden Single Source** | **+12** | **Multi-sourcing** |
    """)

    st.markdown("---")

    # =========================================================================
    # DETTAGLIO NUOVI MODULI v4.0
    # =========================================================================
    st.header("Nuovi Moduli v4.0")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("EMS Risk (Fattore 16 — max +12 pt)")
        st.markdown("""
Valuta il rischio del terzista/EMS su 6 dimensioni:

| Sub-fattore | Max |
|-------------|-----|
| Salute finanziaria (A→D) | 15 pt |
| Utilizzo capacità (>95% = CRITICO) | 15 pt |
| Siti di backup (0 = single-site) | 12 pt |
| Concentrazione geografica | 15 pt |
| Gap certificazioni (IATF16949, ISO9001) | 10 pt |
| Anni di attività (<5 anni) | 5 pt |

Score EMS cappato a **30 pt**, contribuisce al risk engine come +12 pt max.

Se non è disponibile un profilo EMS completo, viene usata solo la stima geografica dalla `EMS_Location`.
        """)

        st.subheader("Hidden Single Source (Fattore 18 — max +12 pt)")
        st.markdown("""
Rileva quando tutte le fonti alternative di un componente
convergono sullo stesso paese di fabbricazione (Frontend_Country).

Esempio: 3 fornitori alternativi tutti con fab in Taiwan
→ diversificazione apparente, rischio reale invariato.

| Overlap ratio | Penalità | Livello |
|---------------|----------|---------|
| 100% (tutte) | +12 pt | CRITICO |
| ≥ 67% | +7 pt | ALTO |
| ≥ 50% | +4 pt | MEDIO |

Richiede fonti alternative registrate in **Gestione Database → Fonti Alternative**.
        """)

    with col2:
        st.subheader("Distributor Risk (Fattore 17 — max +10 pt)")
        st.markdown("""
Valuta il rischio del canale distributivo su 5 dimensioni:

| Sub-fattore | Max |
|-------------|-----|
| Mono-distributore (solo 1 dist.) | 10 pt |
| Stock coverage < lead time | 8 pt |
| Salute finanziaria distributore | 10 pt |
| Lead time markup (settimane aggiuntive) | 5 pt |
| Concentrazione geografica distributore | 5 pt |

Score distributore cappato a **25 pt**, contribuisce al risk engine come +10 pt max.

Se stock coverage ≥ 2× lead time → **bonus −2 pt** (buffer ampio).
        """)

        st.subheader("Tier1→Tier2 Supplier-Specific Linkage")
        st.markdown("""
Gerarchia priorità per le dipendenze materiali:

1. **Component_Materials** custom (override per singolo PN)
2. **Profilo Fornitore** (Key_Materials_Override JSON da Gestione DB)
3. **Default** categoria + technology node

Permette di distinguere:
- STM32 (fab Agrate IT) → wafer Shin-Etsu (JP), non generici Taiwan
- NXP i.MX (fab TSMC) → neon gas Ucraina, photoresists Giappone

I profili fornitore si inseriscono in **Gestione Database → Profili Fornitore**.
        """)

    st.markdown("---")

    # =========================================================================
    # SIMULATORE WHAT-IF — SCENARI
    # =========================================================================
    st.header("Simulatore What-If — Scenari Disponibili")

    st.markdown("""
| Tipo | Scenari predefiniti | Logica impatto |
|------|--------------------|----|
| `country_block` | Taiwan ×2, China ×1 | Moltiplicatore rischio + impatto buffer |
| `lead_time_increase` | +50%, +100% | Aumento proporzionale score lead time |
| `material_shortage` | Neon gas, Photoresists, Terre rare, SiC | Match per materiale e paese |
| `distributor_outage` | Arrow 4w, Avnet 6w | Penalità proporzionale gap buffer/stockout |
| `ems_overload` | Generico 95% capacità | Aumento % score proporzionale a overload |

Il simulatore calcola per ogni componente impattato:
- Settimane di buffer rimanenti dopo la disruption
- Score di rischio aggiustato
- Impatto finanziario stimato (produzione persa × run rate)
    """)

    st.markdown("---")

    # =========================================================================
    # CAMPI DATABASE
    # =========================================================================
    st.header("Campi Database — Valori Ammessi")

    st.markdown("**Part Numbers (foglio principale)**")
    st.markdown("""
| Campo | Valori | Impatto |
|-------|--------|---------|
| EOL_Status | Active, NRND, Last_Buy, EOL, Obsolete | Fattore 8 (+0→+15) |
| Number_of_Alternative_Sources | 0, 1, 2, 3, ... | Fattore 9 |
| Supplier_Financial_Health | A, B, C, D | Fattore 10 |
| Allocation_Status | Normal, Constrained, Allocated | Fattore 11 |
| Last_Price_Increase_Pct | % numerico | Fattore 12 |
| Package_Type | QFP, BGA, WLCSP, QFN, SOP, DIP, CSP, FCBGA | Fattore 13 |
| Technology_Node | es. 7nm, 28nm, 180nm | Fattore 14 |
| Frontend_Country | Paese fab wafer | Fattore 1 + Hidden SPOF |
| Backend_Country | Paese assembly/test | Fattore 1 |
| EMS_Used | Y / N | Fattore 16 |
| EMS_Name | Nome EMS (deve corrispondere a EMS_Providers) | Fattore 16 |
| Automotive_Grade | None, AEC-Q100, AEC-Q101, AEC-Q200 | Moltiplicatore switching |
    """)

    st.markdown("**Fogli aggiuntivi (gestiti via UI)**")
    st.markdown("""
| Foglio | Campi chiave | Uso |
|--------|-------------|-----|
| EMS_Providers | EMS_Name, Country, Financial_Health, Capacity_Utilization_Pct, Backup_Sites_Count, Certifications | Fattore 16 completo |
| Distributors | Name, Country, Financial_Health, Lead_Time_Markup_Weeks, Stock_Level_Weeks_Coverage | Fattore 17 |
| Part_Distributors | Part_Number, Distributor_ID, Priority (Primary/Secondary), Allocation_Pct | Collegamento PN↔Distributore |
| Alt_Sources | Part_Number, Supplier_Name, Frontend_Country, Qualification_Status | Fattore 18 Hidden SPOF |
| Supplier_Profiles | Supplier_Name, Primary_Fab, Primary_Fab_Country, Key_Materials_Override (JSON) | Tier1→Tier2 linkage |
    """)

    st.markdown("---")

    # =========================================================================
    # FLUSSO DI LAVORO
    # =========================================================================
    st.header("Flusso di Lavoro Consigliato")

    st.markdown("""
**Setup iniziale** (una tantum per cliente):
1. **Gestione Database → Gestione Clienti**: aggiungi il cliente e il run rate default
2. **Gestione Database → EMS Providers**: registra i terzisti usati dai componenti
3. **Gestione Database → Distributori**: registra Arrow, Avnet, TTI, ecc. e associali ai Part Numbers
4. **Gestione Database → Fonti Alternative**: per ogni PN critico, inserisci le alternative con `Frontend_Country`
5. **Gestione Database → Profili Fornitore**: per fornitori chiave (STM, NXP, Infineon...), specifica fab e materiali

**Analisi ricorrente** (per ogni revisione BOM):
1. Sidebar: seleziona il cliente
2. **Analisi Multipla**: carica la BOM e avvia l'analisi
3. **Dashboard Esecutiva**: verifica KPI e alert filiera
4. **Filiera Commerciale**: analisi EMS, distributori, hidden SPOF
5. **Simulatore What-If**: testa scenari di disruption (Taiwan, stock-out distributore, EMS overload)
6. **Tier-2/3 Visibility**: verifica bottleneck materiali
7. **Export**: genera report PDF per il management
    """)

    st.markdown("---")

    # =========================================================================
    # CLASSIFICAZIONE
    # =========================================================================
    st.subheader("Classificazione Finale")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="risk-red"><h3>ALTO</h3><p>Score ≥ 55</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="risk-yellow"><h3>MEDIO</h3><p>Score 30–54</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="risk-green"><h3>BASSO</h3><p>Score &lt; 30</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================================
    # LIMITI NOTI
    # =========================================================================
    st.header("Limiti Noti e Roadmap")
    st.markdown("""
| Limite | Workaround attuale | Sviluppo futuro |
|--------|--------------------|-----------------|
| Nessun trend storico | Baseline statica nella Dashboard | Salvataggio analisi per data |
| EMS score parziale senza profilo | Stima da EMS_Location (geo only) | Arricchimento automatico via API |
| Credenziali login hardcoded | Sicure per uso interno | Integrazione LDAP/SSO |
| PDF export non copre tab Filiera | Export da tab Analisi Multipla | Estensione pdf_export.py |
| Nessuna integrazione dati di mercato | Inserimento manuale prezzi e allocation | Feed Octopart/SiliconExpert |
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

def render_tab_filiera_commerciale():
    """Tab Filiera Commerciale: EMS risk, Distributor risk, Hidden Single Source."""
    st.header("Filiera Commerciale")
    st.markdown(
        "Analisi del canale distributivo e del terzista EMS — livelli nascosti della supply chain."
    )

    batch = st.session_state.batch_results
    if not batch:
        st.info("Esegui prima un'**Analisi Multipla** (Tab 2) per caricare i dati della BOM.")
        return

    components_data = batch['components_data']
    components_risk = batch['components_risk']

    # Precarica dati filiera
    db = st.session_state.db
    ems_all = db.get_all_ems_providers()
    ems_by_name = {str(e.get('EMS_Name', '')).upper(): e for e in ems_all}
    all_part_distributors = db.get_all_part_distributors()

    # Analisi aggregate
    ems_analysis = analyze_bom_ems_risk(components_data, ems_by_name)
    dist_analysis = analyze_bom_distributor_risk(components_data, all_part_distributors)

    tab_ems, tab_dist, tab_spof, tab_sim = st.tabs([
        "EMS Risk", "Distributori", "Hidden Single Source", "Simulatore Stock-Out"
    ])

    # =========================================================================
    # SUB-TAB: EMS RISK
    # =========================================================================
    with tab_ems:
        st.subheader("Rischio EMS (Electronics Manufacturing Services)")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Componenti via EMS", ems_analysis['ems_components_count'])
        with col2:
            st.metric("Score Medio EMS", f"{ems_analysis['avg_ems_score']:.1f}/30")
        with col3:
            st.metric("Componenti Critici EMS", len(ems_analysis['critical_ems']))

        st.markdown("---")

        # Tabella componenti con EMS
        ems_rows = []
        for r in ems_analysis['components_ems']:
            if r['ems_used']:
                ems_rows.append({
                    'Part Number': r.get('part_number', ''),
                    'EMS': r.get('ems_name', 'N/A'),
                    'Paese': r.get('ems_country', 'N/A'),
                    'Score EMS': r.get('ems_score', 0),
                    'Livello': r.get('ems_level', 'N/A'),
                    'Profilo': 'Sì' if r.get('has_profile') else 'Stima',
                })
        if ems_rows:
            df_ems = pd.DataFrame(ems_rows).sort_values('Score EMS', ascending=False)
            def _color_ems(row):
                score = row['Score EMS']
                if score >= 20:
                    return ['background-color: #ff444433'] * len(row)
                elif score >= 12:
                    return ['background-color: #ffbb3333'] * len(row)
                return [''] * len(row)
            st.dataframe(df_ems.style.apply(_color_ems, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("Nessun componente usa EMS (o campo EMS_Used non impostato)")

        if ems_analysis['shared_ems_risks']:
            st.markdown("---")
            st.subheader("EMS Condivisi (SPOF Potenziale)")
            for shared in ems_analysis['shared_ems_risks']:
                badge = "🔴 Single-site" if shared['is_single_site'] else f"🔵 {shared['backup_sites']} backup"
                st.warning(
                    f"**{shared['ems_name']}** usato da **{shared['affected_count']} componenti** {badge}: "
                    f"{', '.join(shared['affected_pns'][:5])}"
                )

    # =========================================================================
    # SUB-TAB: DISTRIBUTORI
    # =========================================================================
    with tab_dist:
        st.subheader("Rischio Distributore")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Componenti con Distributore", len([r for r in dist_analysis['components_distributor'] if r['has_distributors']]))
        with col2:
            st.metric("Score Medio Distributore", f"{dist_analysis['avg_distributor_score']:.1f}/25")
        with col3:
            st.metric("Mono-Distributore", len(dist_analysis['mono_distributor_pns']))
        with col4:
            st.metric("Senza Distributore", len(dist_analysis['no_distributor_pns']))

        st.markdown("---")

        # Tabella
        dist_rows = []
        for r in dist_analysis['components_distributor']:
            dist_rows.append({
                'Part Number': r.get('part_number', ''),
                'Distributore Primario': r.get('primary_distributor', 'N/A'),
                'N. Distributori': r.get('distributor_count', 0),
                'Score': r.get('distributor_score', 0),
                'Livello': r.get('distributor_level', 'N/A') if r.get('has_distributors') else '—',
                'Stock Coverage (w)': r.get('stock_coverage_weeks', 0),
                'LT Markup (w)': r.get('lead_time_markup_weeks', 0),
            })
        if dist_rows:
            df_dist = pd.DataFrame(dist_rows).sort_values('Score', ascending=False)
            def _color_dist(row):
                score = row['Score']
                if score >= 18:
                    return ['background-color: #ff444433'] * len(row)
                elif score >= 10:
                    return ['background-color: #ffbb3333'] * len(row)
                return [''] * len(row)
            st.dataframe(df_dist.style.apply(_color_dist, axis=1), use_container_width=True, hide_index=True)

        if dist_analysis['top_shared_distributors']:
            st.markdown("---")
            st.subheader("Distributori Condivisi (SPOF Potenziale)")
            for shared in dist_analysis['top_shared_distributors']:
                icon = "🔴 SPOF" if shared['is_spof'] else "🟡"
                st.warning(
                    f"{icon} **{shared['distributor']}** → {shared['affected_count']} PN: "
                    f"{', '.join(shared['affected_pns'][:6])}"
                )

        if dist_analysis['no_distributor_pns']:
            st.markdown("---")
            st.info(
                f"**{len(dist_analysis['no_distributor_pns'])} PN senza distributore registrato**: "
                + ", ".join(dist_analysis['no_distributor_pns'][:8])
                + (" …" if len(dist_analysis['no_distributor_pns']) > 8 else "")
            )

    # =========================================================================
    # SUB-TAB: HIDDEN SINGLE SOURCE
    # =========================================================================
    with tab_spof:
        st.subheader("Hidden Single Source Detection")
        st.markdown("""
        Un componente ha **hidden single source** quando tutte le sue fonti alternative
        (inclusa la primaria) convergono sullo stesso paese di fabbricazione frontend.
        Avere 3 fornitori tutti con fab in Taiwan non diversifica il rischio geopolitico.
        """)

        hidden_components = [
            r for r in components_risk
            if r.get('hidden_single_source', {}).get('hidden_spof_score', 0) >= 4
        ]

        if not hidden_components:
            st.success(
                "Nessun hidden single source rilevato nella BOM attuale. "
                "Aggiungi fonti alternative nel tab Gestione Database → Fonti Alternative "
                "per abilitare il rilevamento."
            )
        else:
            st.error(f"**{len(hidden_components)} componenti con hidden single source**")

            for r in hidden_components:
                hs = r.get('hidden_single_source', {})
                pn = r.get('part_number', 'N/A')
                overlap_country = hs.get('overlap_country', 'N/A').title()
                overlap_count = hs.get('overlap_count', 0)
                total_sources = hs.get('total_sources', 0)
                level = hs.get('level', 'N/A')
                score = hs.get('hidden_spof_score', 0)

                with st.expander(f"⚠️ {pn} — {level} (score +{score}) — {overlap_country}"):
                    st.markdown(f"""
                    - **Paese convergente:** {overlap_country}
                    - **Fonti su quel paese:** {overlap_count} di {total_sources}
                    - **Livello:** {level}
                    - **Suggerimento:** Qualificare un fornitore alternativo con fab in paese diverso da {overlap_country}
                    """)

        st.markdown("---")
        st.subheader("Tutte le Fonti Alternative Registrate")
        all_alt = db.get_all_alt_sources()
        if all_alt:
            rows = []
            for pn_key, sources in all_alt.items():
                for s in sources:
                    rows.append({'Part Number': pn_key, **{k: v for k, v in s.items() if k != 'Part_Number'}})
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info(
                "Nessuna fonte alternativa nel DB. "
                "Aggiungile in Gestione Database → Fonti Alternative per attivare il rilevamento."
            )

    # =========================================================================
    # SUB-TAB: SIMULATORE STOCK-OUT DISTRIBUTORE
    # =========================================================================
    with tab_sim:
        st.subheader("Simulatore Stock-Out Distributore")
        st.markdown(
            "Simula l'impatto di uno stock-out su un distributore specifico: "
            "quali componenti restano scoperti e per quante settimane."
        )

        # Ottieni lista distributori dalla BOM corrente
        active_distributors = set()
        for r in dist_analysis['components_distributor']:
            if r.get('has_distributors') and r.get('primary_distributor') != 'N/A':
                active_distributors.add(r['primary_distributor'])

        if not active_distributors:
            st.info("Nessun distributore associato alla BOM. Aggiungi distribuzioni in Gestione Database → Distributori.")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            target_dist = st.selectbox("Distributore da simulare", sorted(active_distributors))
        with col2:
            stockout_weeks = st.slider("Settimane di stock-out", 1, 26, 4)
        with col3:
            sim_run_rate = st.number_input(
                "Run Rate (PCB/sett.)", min_value=1, value=st.session_state.run_rate
            )

        if st.button("Esegui Simulazione", type="primary"):
            sim_result = simulate_distributor_stockout(
                components_data, all_part_distributors,
                target_dist, stockout_weeks, sim_run_rate
            )

            summary = sim_result['summary']
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Componenti Impattati", summary['total_affected'])
            with col2:
                st.metric("Componenti Critici", summary['total_critical'], help="Buffer esaurito prima della fine dello stock-out")
            with col3:
                st.metric("Settimane Perse (media)", f"{summary['avg_weeks_lost']:.1f}")

            if sim_result['affected_components']:
                affected_df = pd.DataFrame(sim_result['affected_components'])
                def _color_critical(row):
                    if row['is_critical']:
                        return ['background-color: #ff444433'] * len(row)
                    return [''] * len(row)
                st.dataframe(
                    affected_df.style.apply(_color_critical, axis=1),
                    use_container_width=True, hide_index=True
                )
            else:
                st.success(f"Nessun componente impattato da uno stock-out di {target_dist}")


def _run_batch_analysis(pns: List[str], client_id, run_rate):
    """Esegue analisi batch e restituisce risultati strutturati. v4.0: include EMS, distributori, alt sources."""
    from risk_engine import calculate_bom_risk_v3

    results = st.session_state.db.lookup_batch(pns, client_id)
    found_components = {pn: data for pn, data in results.items() if data is not None}
    not_found = [pn for pn, data in results.items() if data is None]

    if not found_components:
        return None

    # v4.0 - Carica dati filiera commerciale dal DB
    db = st.session_state.db

    # EMS providers indicizzati per nome (uppercase)
    ems_all = db.get_all_ems_providers()
    ems_by_name = {str(e.get('EMS_Name', '')).upper(): e for e in ems_all}

    # Distributori associati per PN
    all_part_distributors = db.get_all_part_distributors()

    # Fonti alternative per PN
    all_alt_sources = db.get_all_alt_sources()

    # Profili fornitore per nome (uppercase)
    supplier_profiles_all = db.get_all_supplier_profiles()
    supplier_profiles_by_name = {str(s.get('Supplier_Name', '')).upper(): s for s in supplier_profiles_all}

    # Calcola rischi individuali
    components_data = []
    components_risk = []
    for pn, data in found_components.items():
        pn_upper = pn.upper()

        # Recupera dati filiera per questo PN
        ems_name = str(data.get('EMS_Name', '') or '').upper()
        ems_profile = ems_by_name.get(ems_name) if ems_name else None

        dist_list = all_part_distributors.get(pn_upper, [])
        alt_sources = all_alt_sources.get(pn_upper, [])

        supplier_name = str(data.get('Supplier Name', '') or '').upper()
        supplier_profile = supplier_profiles_by_name.get(supplier_name)

        risk = calculate_component_risk(
            data, run_rate,
            ems_provider_data=ems_profile,
            distributor_list=dist_list,
            alt_sources=alt_sources,
        )
        risk['part_number'] = pn
        risk['supplier'] = data.get('Supplier Name', 'N/A')
        risk['category'] = data.get('Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)', 'N/A')
        risk['supplier_profile'] = supplier_profile  # Per tier2 con profilo fornitore
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
