"""
costi_switching.py — Tab: render_tab_costi_switching
"""

from pdf_export import show_export_button
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_tab_costi_switching():
    """Tab 5: Switching Cost Analysis"""
    st.header("Switching Cost Analysis")
    st.markdown("""
    Estimate of the man-hour cost to replace each component, based on:
    - **SW Porting**: code size x OS complexity (Baremetal/RTOS/Linux)
    - **Qualification**: qualification weeks x 40 hours/week
    - **Certification**: multiplier by certification type (AEC-Q100, MIL-STD, etc.)
    """)

    batch = st.session_state.batch_results
    if batch:
        # PDF export button
        st.subheader("Export Report")
        show_export_button(batch, st.session_state.current_client, st.session_state.run_rate, key="export_tab_switching")
        st.markdown("---")
        components_risk = batch['components_risk']

        # Main table
        sw_table = []
        for risk in components_risk:
            sw = risk.get('switching_cost', {})
            sw_table.append({
                'Part Number': risk.get('part_number', 'N/A'),
                'Supplier': risk.get('supplier', 'N/A'),
                'Category': risk.get('category', 'N/A'),
                'OS': sw.get('os_type', 'N/A'),
                'SW Size (KB)': sw.get('sw_size_kb', 0),
                'Porting (h)': sw.get('sw_porting_hours', 0),
                'Qualification (h)': sw.get('qualification_hours', 0),
                'Cert. Mult.': sw.get('certification_multiplier', 1.0),
                'Total (h)': sw.get('total_switching_hours', 0),
                'Classification': sw.get('classification', 'N/A'),
            })

        df_sw = pd.DataFrame(sw_table)
        df_sw = df_sw.sort_values('Total (h)', ascending=False)

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            critical = sum(1 for r in sw_table if r['Classification'] == 'CRITICO')
            st.metric("CRITICAL", critical)
        with col2:
            complex_ = sum(1 for r in sw_table if r['Classification'] == 'COMPLESSO')
            st.metric("COMPLEX", complex_)
        with col3:
            moderate = sum(1 for r in sw_table if r['Classification'] == 'MODERATO')
            st.metric("MODERATE", moderate)
        with col4:
            trivial = sum(1 for r in sw_table if r['Classification'] == 'TRIVIALE')
            st.metric("TRIVIAL", trivial)

        # Table
        st.dataframe(df_sw, use_container_width=True, hide_index=True)

        # Horizontal bar chart
        fig_sw = go.Figure()

        color_map = {
            'TRIVIALE': '#00C851', 'MODERATO': '#ffbb33',
            'COMPLESSO': '#ff8800', 'CRITICO': '#ff4444'
        }
        colors = [color_map.get(row['Classification'], '#888') for _, row in df_sw.iterrows()]

        fig_sw.add_trace(go.Bar(
            y=df_sw['Part Number'],
            x=df_sw['Total (h)'],
            orientation='h',
            marker_color=colors,
            text=[f"{h:.0f}h ({c})" for h, c in zip(df_sw['Total (h)'], df_sw['Classification'])],
            textposition='auto'
        ))
        fig_sw.update_layout(
            title="Switching Cost per Component (man-hours)",
            xaxis_title="Man-Hours",
            yaxis_title="Component",
            showlegend=False,
            height=max(300, len(df_sw) * 40 + 100),
            yaxis={'categoryorder': 'total ascending'}
        )
        fig_sw.add_vline(x=100, line_dash="dash", line_color="green", annotation_text="TRIVIAL")
        fig_sw.add_vline(x=500, line_dash="dash", line_color="orange", annotation_text="MODERATE")
        fig_sw.add_vline(x=2000, line_dash="dash", line_color="red", annotation_text="COMPLEX")
        st.plotly_chart(fig_sw, use_container_width=True)

        # Breakdown detail for critical/complex components
        critical_components = [r for r in components_risk if r.get('switching_cost', {}).get('classification') in ('CRITICO', 'COMPLESSO')]
        if critical_components:
            st.subheader("Breakdown of Critical/Complex Components")
            for risk in critical_components:
                sw = risk.get('switching_cost', {})
                with st.expander(f"**{risk['part_number']}** - {sw.get('classification', 'N/A')} ({sw.get('total_switching_hours', 0):.0f}h)"):
                    for item in sw.get('breakdown', []):
                        st.markdown(f"- {item['item']}: **{item['hours']:.0f}h**")
                    st.markdown(f"**{sw.get('description', '')}**")
    else:
        st.info("Run a **Multiple Analysis** (Tab 2) first to view switching costs.")


# =============================================================================
# TAB 6: DATABASE MANAGEMENT
# =============================================================================

