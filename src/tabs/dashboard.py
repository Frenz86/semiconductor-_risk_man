"""
dashboard.py — Tab: render_tab_dashboard_esecutiva
"""

from pdf_export import show_export_button
from excel_export import show_excel_export_button
from alert_engine import check_kri_alerts, get_alert_summary
import pandas as pd
import plotly.express as px
import streamlit as st


def render_tab_dashboard_esecutiva():
    """Tab 8: Dashboard Esecutiva - One-pager per il management"""
    st.header("📊 Executive Dashboard")
    st.markdown("**One-pager with main KPIs for strategic decisions**")

    batch = st.session_state.batch_results
    if not batch:
        st.info("Run a **Multiple Analysis** (Tab 2) first to display the dashboard.")
        return

    components_data = batch['components_data']
    components_risk = batch['components_risk']
    bom_risk = batch['bom_risk']

    # =============================================================================
    # SEZIONE 0: KRI ALERT BANNER (v4.3)
    # =============================================================================
    _client_id = st.session_state.get('current_client', '')
    _appetite = st.session_state.db.get_client_risk_appetite(_client_id) if _client_id else {'high': 55, 'medium': 30}
    _kri_alerts = check_kri_alerts(batch, risk_appetite=_appetite)

    if _kri_alerts:
        _summary = get_alert_summary(_kri_alerts)
        if _summary['CRITICAL'] > 0:
            st.error(
                f"**KRI ALERT — {_summary['CRITICAL']} componenti CRITICAL** "
                f"superano la soglia HIGH ({_appetite['high']}). "
                f"Vedi dettaglio sotto."
            )
        if _summary['HIGH'] > 0:
            st.warning(
                f"**{_summary['HIGH']} nuovi componenti HIGH** rispetto all'analisi precedente."
            )
        if _summary['WARNING'] > 0:
            st.warning(
                f"**{_summary['WARNING']} componenti** con score aumentato >{10} punti."
            )

        with st.expander(f"Dettaglio KRI Alerts ({_summary['total']} alert)", expanded=False):
            for al in _kri_alerts:
                _icon = {'CRITICAL': '🔴', 'HIGH': '🟠', 'WARNING': '🟡'}.get(al['severity'], '⚪')
                st.markdown(f"{_icon} **{al['severity']}** — {al['message']}")

    # =============================================================================
    # SEZIONE 1: KPI PRINCIPALI
    # =============================================================================
    st.subheader("Main KPIs")

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
            category_risk_matrix[cat] = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'count': 0}
        category_risk_matrix[cat][level] += 1
        category_risk_matrix[cat]['count'] += 1

    # =============================================================================
    # DISPLAY KPI
    # =============================================================================
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6 = st.columns(6)

    with kpi_col1:
        st.metric("Average Risk", f"{avg_score:.1f}", delta="Low" if avg_score < 30 else "Medium" if avg_score < 55 else "High")

    with kpi_col2:
        st.metric("High Risk", red_count, delta=f"{red_count}/{len(risks)}")

    with kpi_col3:
        st.metric("BOM Value", f"${total_bom_value:,.0f}")

    with kpi_col4:
        st.metric("Total Man-Hours", f"{total_mh:,}h")

    with kpi_col5:
        st.metric("SPOF", spof_count)

    with kpi_col6:
        bom_level = bom_risk.get('risk_level', 'N/A')
        st.metric("BOM Risk", bom_level)

    st.markdown("---")

    # =============================================================================
    # SEZIONE 2: GRAFICI PRINCIPALI
    # =============================================================================
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Pie chart distribuzione rischio
        risk_counts = {
            'High (RED)': red_count,
            'Medium (YELLOW)': yellow_count,
            'Low (GREEN)': green_count
        }
        fig_pie = px.pie(
            values=list(risk_counts.values()),
            names=list(risk_counts.keys()),
            color=list(risk_counts.keys()),
            color_discrete_map={
                'High (RED)': '#ff4444',
                'Medium (YELLOW)': '#ffbb33',
                'Low (GREEN)': '#00C851'
            },
            title="Risk Distribution",
            hole=0.4
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col2:
        # Bar chart fornitori a rischio
        if supplier_risk:
            supp_df = pd.DataFrame([
                {'Supplier': s, 'Average Risk': d['avg'], 'Count': d['count'], 'Red': d['red']}
                for s, d in supplier_risk.items()
            ]).sort_values('Average Risk', ascending=False).head(10)

            colors = ['#ff4444' if r >= 55 else '#ffbb33' if r >= 30 else '#00C851' for r in supp_df['Average Risk']]
            fig_supp = px.bar(
                supp_df,
                x='Average Risk',
                y='Supplier',
                orientation='h',
                color='Average Risk',
                color_continuous_scale=['#00C851', '#ffbb33', '#ff4444'],
                title="Top 10 Suppliers by Average Risk",
                text='Average Risk'
            )
            fig_supp.update_traces(texttemplate='%{text:.1f}', textposition='auto')
            fig_supp.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_supp, use_container_width=True)

    st.markdown("---")

    # =============================================================================
    # SEZIONE 2B: P×I RISK MATRIX (ISO 31000)
    # =============================================================================
    st.subheader("📊 Probability × Impact Risk Matrix")

    px_data = [
        {
            'Part Number': r.get('part_number', ''),
            'Supplier': r.get('supplier', ''),
            'Probability': r.get('px_probability', 1),
            'Impact': r.get('px_impact', 1),
            'P×I Score': r.get('px_score', 1),
            'Risk Level': r.get('risk_level', 'LOW'),
            'Score': r.get('score', 0),
        }
        for r in risks if r.get('px_score') is not None
    ]

    if px_data:
        df_px = pd.DataFrame(px_data)
        color_map = {'HIGH': '#ff4444', 'MEDIUM': '#ffbb33', 'LOW': '#00C851'}
        fig_px = px.scatter(
            df_px,
            x='Probability',
            y='Impact',
            color='Risk Level',
            color_discrete_map=color_map,
            size='P×I Score',
            hover_data=['Part Number', 'Supplier', 'Score', 'P×I Score'],
            title='P×I Risk Matrix (ISO 31000)',
            labels={'Probability': 'Probability (1-5)', 'Impact': 'Impact (1-5)'},
            range_x=[0.5, 5.5],
            range_y=[0.5, 5.5],
        )
        # Zone colorate di sfondo
        fig_px.add_shape(type='rect', x0=0.5, y0=0.5, x1=2.5, y1=2.5,
                         fillcolor='#e8f5e9', opacity=0.3, line_width=0)
        fig_px.add_shape(type='rect', x0=2.5, y0=2.5, x1=5.5, y1=5.5,
                         fillcolor='#ffebee', opacity=0.3, line_width=0)
        fig_px.update_layout(height=380, xaxis=dict(tickmode='linear', dtick=1),
                              yaxis=dict(tickmode='linear', dtick=1))
        st.plotly_chart(fig_px, use_container_width=True)
        st.caption("Size = P×I score (1-25). Top-right = high risk zone. Bottom-left = low risk zone.")
    else:
        st.info("Run a Multiple Analysis to display the P×I matrix.")

    st.markdown("---")

    # =============================================================================
    # SEZIONE 3: HEAT MAP CATEGORIE x LIVELLO RISCHIO
    # =============================================================================
    st.subheader("🔥 Heat Map: Categories x Risk Level")

    if category_risk_matrix:
        heatmap_data = []
        for cat, levels in category_risk_matrix.items():
            total = levels['count']
            heatmap_data.append({
                'Category': cat,
                'HIGH': levels['HIGH'],
                'MEDIUM': levels['MEDIUM'],
                'LOW': levels['LOW'],
                'Total': total
            })

        df_heatmap = pd.DataFrame(heatmap_data).sort_values('Total', ascending=False)

        # Color table display
        def highlight_risk(val, col):
            if col == 'Category' or col == 'Total':
                return ''
            if val > 0:
                if col == 'HIGH':
                    return 'background-color: #ff4444; color: white; font-weight: bold;'
                elif col == 'MEDIUM':
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
    st.subheader("🚨 Top 10 Components at Risk")

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

        # Risk Owner da Client_Data
        client_id = st.session_state.get('current_client', '')
        pn = r.get('part_number', '')
        owner_info = st.session_state.db.get_risk_owner(client_id, pn) if client_id and pn else {'owner': '', 'status': ''}

        top10_data.append({
            'Rank': i,
            'Part Number': pn or 'N/A',
            'Supplier': r.get('supplier', 'N/A'),
            'Score': r['score'],
            'Level': r['risk_level'],
            'Lead Time (w)': lead_time,
            'Geo Score': geo.get('composite_score', 0),
            'Switching': sw.get('classification', 'N/A'),
            'SPOF': 'Yes' if any('solo stabilimento' in f.lower() for f in r['factors']) else 'No',
            'Owner': owner_info['owner'] or '—',
            'Status': owner_info['status'] or '—',
        })

    df_top10 = pd.DataFrame(top10_data)

    # Color rows by risk level
    def color_row(row):
        if row['Level'] == 'HIGH':
            return ['background-color: #ff444433'] * len(row)
        elif row['Level'] == 'MEDIUM':
            return ['background-color: #ffbb3333'] * len(row)
        return [''] * len(row)

    styled_top10 = df_top10.style.apply(color_row, axis=1)
    st.dataframe(styled_top10, use_container_width=True, hide_index=True)

    st.markdown("---")

    # =============================================================================
    # SEZIONE 4b: ALERT FILIERA COMMERCIALE (v4.0)
    # =============================================================================
    st.subheader("🔗 Commercial Supply Chain Alerts")

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
            st.error(f"**Hidden Single Source: {len(hidden_spof_list)} components**")
            st.markdown(
                "These components have alternative sources but share the same fab country:"
            )
            for r in hidden_spof_list[:5]:
                hs = r.get('hidden_single_source', {})
                st.markdown(
                    f"- **{r.get('part_number')}** – {hs.get('overlap_country', '?').title()} "
                    f"({hs.get('overlap_count', 0)}/{hs.get('total_sources', 0)} sources)"
                )
        else:
            st.success("No Hidden Single Source detected")

    with filiera_col2:
        if mono_dist_list:
            st.warning(f"**Single-Distributor: {len(mono_dist_list)} components**")
            for r in mono_dist_list[:5]:
                dist = r.get('distributor_risk', {})
                st.markdown(
                    f"- **{r.get('part_number')}** → {dist.get('primary_distributor', 'N/A')}"
                )
        else:
            st.success("No single-distributor components")

    with filiera_col3:
        if ems_spof_list:
            st.warning(f"**High-risk EMS: {len(ems_spof_list)} components**")
            for r in ems_spof_list[:5]:
                ems = r.get('ems_risk', {})
                st.markdown(
                    f"- **{r.get('part_number')}** – {ems.get('ems_name', 'N/A')} "
                    f"(score {ems.get('ems_score', 0)})"
                )
        else:
            st.success("No critical EMS")

    st.markdown("---")

    # =============================================================================
    # SEZIONE 5: RIEPILOGO AZIONI RACCOMANDATE
    # =============================================================================
    st.subheader("✅ Recommended Actions by Priority")

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
        st.markdown("### 🔴 Urgent")
        if urgent_actions:
            for action in urgent_actions[:5]:
                st.markdown(f"- {action}")
        else:
            st.info("No urgent actions")

    with action_col2:
        st.markdown("### 🟠 High Priority")
        if high_priority_actions:
            for action in high_priority_actions[:5]:
                st.markdown(f"- {action}")
        else:
            st.info("No high-priority actions")

    with action_col3:
        st.markdown("### 🟡 Medium Priority")
        if medium_priority_actions:
            for action in medium_priority_actions[:5]:
                st.markdown(f"- {action}")
        else:
            st.info("No medium-priority actions")

    st.markdown("---")

    # =============================================================================
    # SEZIONE 6: TREND STORICO REALE
    # =============================================================================
    st.subheader("📈 Risk Trend Over Time")

    client_id = st.session_state.get('current_client')
    history_df = st.session_state.db.get_analysis_history(client_id=client_id)

    if history_df.empty:
        st.info("No historical data yet. Run multiple analyses over time to see the trend.")
        col_trend1, col_trend2, col_trend3 = st.columns(3)
        with col_trend1:
            st.markdown("**Current Baseline**")
            st.metric("Date", pd.Timestamp.now().strftime('%Y-%m-%d'))
            st.metric("Average Score", f"{avg_score:.1f}")
            st.metric("Critical Components", red_count)
        with col_trend2:
            st.markdown("**Target -3 months**")
            st.metric("Target Score", f"{avg_score * 0.85:.1f}", "-15%")
            st.metric("Target Critical", max(0, red_count - red_count // 2))
        with col_trend3:
            st.markdown("**Target -6 months**")
            st.metric("Target Score", f"{avg_score * 0.7:.1f}", "-30%")
            st.metric("Target Critical", max(0, red_count * 2 // 3))
    else:
        # Grafico linee interattivo con dati reali
        fig_trend = px.line(
            history_df,
            x='Timestamp',
            y='Avg_Risk_Score',
            color='BOM_Name',
            markers=True,
            title='Average Risk Score Over Time',
            labels={'Avg_Risk_Score': 'Avg Risk Score', 'Timestamp': 'Analysis Date', 'BOM_Name': 'BOM'},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_trend.add_hline(y=55, line_dash='dash', line_color='red', annotation_text='HIGH threshold (55)')
        fig_trend.add_hline(y=30, line_dash='dash', line_color='orange', annotation_text='MEDIUM threshold (30)')
        fig_trend.update_layout(height=350, margin=dict(t=40, b=20))
        st.plotly_chart(fig_trend, use_container_width=True)

        # KPI variazione rispetto alla prima analisi
        first_score = history_df.iloc[0]['Avg_Risk_Score']
        last_score = history_df.iloc[-1]['Avg_Risk_Score']
        delta = last_score - first_score
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            st.metric("Analyses Saved", len(history_df))
        with col_h2:
            st.metric("First Score", f"{first_score:.1f}")
        with col_h3:
            st.metric("Latest Score", f"{last_score:.1f}", f"{delta:+.1f} vs first")

    st.markdown("---")

    # =============================================================================
    # SEZIONE 7: EXPORT
    # =============================================================================
    st.subheader("📄 Export Dashboard")

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        show_export_button(batch, st.session_state.current_client, st.session_state.run_rate, key="export_dashboard")
    with col_exp2:
        show_excel_export_button(batch, st.session_state.current_client, st.session_state.run_rate, key="excel_dashboard")


# =============================================================================
# TAB 9: GUIDA
# =============================================================================

