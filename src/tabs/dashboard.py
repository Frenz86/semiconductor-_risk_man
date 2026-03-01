"""
dashboard.py — Tab: render_tab_dashboard_esecutiva
"""

from pdf_export import show_export_button
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
        st.plotly_chart(fig_pie, use_container_use_container_width=True)

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
            st.plotly_chart(fig_supp, use_container_use_container_width=True)

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

        top10_data.append({
            'Rank': i,
            'Part Number': r.get('part_number', 'N/A'),
            'Supplier': r.get('supplier', 'N/A'),
            'Score': r['score'],
            'Level': r['risk_level'],
            'Lead Time (w)': lead_time,
            'Geo Score': geo.get('composite_score', 0),
            'Switching': sw.get('classification', 'N/A'),
            'SPOF': 'Yes' if any('solo stabilimento' in f.lower() for f in r['factors']) else 'No'
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
    # SEZIONE 6: TREND TEMPORE (simulato - base per futuro sviluppo)
    # =============================================================================
    st.subheader("📈 Risk Trend Over Time")

    st.info("""
    **Note**: The historical trend requires saving analyses over time.
    This section will show the evolution of BOM risk across different versions.

    *To enable this feature, implement historical analysis saving.*
    """)

    # Mostra solo la situazione corrente come baseline
    col_trend1, col_trend2, col_trend3 = st.columns(3)

    with col_trend1:
        st.markdown("**Current Baseline**")
        st.metric("Date", pd.Timestamp.now().strftime('%Y-%m-%d'))
        st.metric("Average Score", f"{avg_score:.1f}")
        st.metric("Critical Components", red_count)

    with col_trend2:
        st.markdown("**Target -3 months**")
        target_reduction = avg_score * 0.85  # -15%
        st.metric("Target Score", f"{target_reduction:.1f}", "-15%")
        st.metric("Target Critical", max(0, red_count - red_count // 2))

    with col_trend3:
        st.markdown("**Target -6 months**")
        target_reduction_6m = avg_score * 0.7  # -30%
        st.metric("Target Score", f"{target_reduction_6m:.1f}", "-30%")
        st.metric("Target Critical", max(0, red_count * 2 // 3))

    st.markdown("---")

    # =============================================================================
    # SEZIONE 7: EXPORT
    # =============================================================================
    st.subheader("📄 Export Dashboard")

    show_export_button(batch, st.session_state.current_client, st.session_state.run_rate, key="export_dashboard")


# =============================================================================
# TAB 9: GUIDA
# =============================================================================

