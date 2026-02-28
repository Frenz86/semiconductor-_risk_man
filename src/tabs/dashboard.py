"""
dashboard.py — Tab: render_tab_dashboard_esecutiva
"""

from pdf_export import show_export_button
import pandas as pd
import plotly.express as px
import streamlit as st


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

