"""
costi_switching.py — Tab: render_tab_costi_switching
"""

from pdf_export import show_export_button
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


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

