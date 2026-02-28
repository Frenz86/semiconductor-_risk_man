"""
analisi_rapida.py — Tab: render_tab_analisi_rapida
"""

from risk_engine import calculate_component_risk
import streamlit as st


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

_QTY_COL = 'How Many Device of this specific PN are in the BOM?'
_BUF_COL = 'If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units'

