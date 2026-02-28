"""
albero_dipendenze.py — Tab: render_tab_albero_dipendenze
"""

from dependency_graph import HAS_NETWORKX
import pandas as pd
import streamlit as st


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

