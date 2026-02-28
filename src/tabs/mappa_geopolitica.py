"""
mappa_geopolitica.py — Tab: render_tab_mappa_geopolitica
"""

from geo_risk import get_technology_node_risk, generate_risk_map_data
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


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

