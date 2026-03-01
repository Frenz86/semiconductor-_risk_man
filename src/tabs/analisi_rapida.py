"""
analisi_rapida.py — Tab: render_tab_analisi_rapida
"""

from risk_engine import calculate_component_risk
import streamlit as st
from ._shared import render_risk_badge, render_switching_badge, render_geo_detail


def render_tab_analisi_rapida():
    """Tab 1: Analisi Rapida Part Number"""
    st.header("Quick Analysis Part Number")

    col1, col2 = st.columns([3, 1])

    with col1:
        pn_input = st.text_input(
            "Enter Part Number",
            placeholder="e.g. STM32MP157CAC3",
            key="pn_single_input"
        ).strip()

    with col2:
        st.write("")
        st.write("")
        analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

    if analyze_btn and pn_input:
        component_data = st.session_state.db.lookup_part_number(
            pn_input, st.session_state.current_client
        )

        if component_data:
            st.success(f"Part Number **{pn_input}** found in the database!")

            # Carica market shortage, alt sources e IP dependencies per questo PN
            market_shortage = st.session_state.db.get_market_shortage()
            alt_sources = st.session_state.db.get_alt_sources(pn_input)
            ip_deps = st.session_state.db.get_ip_dependencies(pn_input)

            # Calcola rischio v5
            risk = calculate_component_risk(
                component_data, st.session_state.run_rate,
                alt_sources=alt_sources,
                market_shortage=market_shortage,
                ip_dependencies=ip_deps,
            )

            # Dashboard principale
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                render_risk_badge(risk['risk_level'], risk['score'])

            with col2:
                st.metric("Mitigation Man-Hours", f"{risk['man_hours']}h")

            with col3:
                st.metric("Risk Factors", len(risk['factors']))

            with col4:
                switching = risk.get('switching_cost', {})
                st.metric("Switching Cost", f"{switching.get('total_switching_hours', 0):.0f}h")
                render_switching_badge(switching.get('classification', 'N/A'))

            # Dettaglio Geo Risk Frontend/Backend
            st.subheader("Geopolitical Risk Frontend/Backend")
            geo = risk.get('geo_risk', {})
            col1, col2, col3 = st.columns(3)

            with col1:
                render_geo_detail(geo)

            with col2:
                tech = risk.get('tech_node_risk', {})
                if tech.get('nm'):
                    st.markdown(f"**Technology Node:** {tech['nm']}nm")
                    st.markdown(f"**Risk:** {tech['level']}")
                    st.markdown(f"*{tech['reason']}*")
                else:
                    st.info("Technology node not specified")

            with col3:
                st.metric("Composite Geo Score", f"{geo.get('composite_score', 0):.1f}/25")
                st.markdown(f"Frontend: {geo.get('frontend_score', 0)}/25 (weight 60%)")
                st.markdown(f"Backend: {geo.get('backend_score', 0)}/15 (weight 40%)")

            # Dettaglio Switching Cost
            if switching.get('breakdown'):
                st.subheader("Switching Cost Breakdown")
                for item in switching['breakdown']:
                    st.markdown(f"- **{item['item']}**: {item['hours']:.0f} hours")
                st.markdown(f"**Total: {switching.get('total_switching_hours', 0):.0f} hours - {switching.get('classification', 'N/A')}**")

            # Fattori e suggerimenti
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Risk Factors")
                if risk['factors']:
                    for factor in risk['factors']:
                        st.markdown(f"- {factor}")
                else:
                    st.info("No significant risk factors")

            with col2:
                st.subheader("Suggestions")
                if risk['suggestions']:
                    for suggestion in risk['suggestions']:
                        st.markdown(f"- {suggestion}")
                else:
                    st.info("No action required")

            # ---------------------------------------------------------------
            # SHORTAGE ALERT
            # ---------------------------------------------------------------
            shortage = risk.get('shortage_impact', {})
            if shortage.get('affected'):
                ifaces = ', '.join(shortage['affected_interfaces'])
                st.warning(
                    f"⚠️ **Market shortage detected** — {ifaces} "
                    f"(severity: **{shortage['severity']}**). "
                    "Consider alternatives with a different interface."
                )
                for note in shortage.get('shortage_notes', []):
                    st.caption(f"  • {note}")

            # ---------------------------------------------------------------
            # ALTERNATIVE CONSIGLIATE
            # ---------------------------------------------------------------
            alternatives = risk.get('suggested_alternatives', [])
            if alternatives:
                st.subheader("Recommended Alternatives")
                _render_alternatives_table(alternatives)
            elif alt_sources:
                st.info("Alternative sources available but no compatibility data found. "
                        "Add `Interface_Type` and `Drop_In_Replacement` in Database Management.")

            # Dati componente
            with st.expander("Full Component Data"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Supplier:** {component_data.get('Supplier Name', 'N/A')}")
                    st.markdown(f"**Category:** {component_data.get('Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)', 'N/A')}")
                    st.markdown(f"**Lead Time:** {component_data.get('Supplier Lead Time (weeks)', 'N/A')} weeks")
                    st.markdown(f"**Price:** ${component_data.get('Unit Price ($)', 'N/A')}")
                with col2:
                    countries = [c for c in [
                        component_data.get('Country of Manufacturing Plant 1'),
                        component_data.get('Country of Manufacturing Plant 2'),
                        component_data.get('Country of Manufacturing Plant 3'),
                        component_data.get('Country of Manufacturing Plant 4')
                    ] if c and str(c).strip()]
                    st.markdown(f"**Manufacturing Countries:** {', '.join(str(c) for c in countries) if countries else 'N/A'}")
                    st.markdown(f"**Proprietary:** {component_data.get('Proprietary (Y/N)**', 'N/A')}")
                    st.markdown(f"**Commodity:** {component_data.get('Commodity (Y/N)*', 'N/A')}")
                    st.markdown(f"**Stand-Alone:** {component_data.get('Stand-Alone Functional Device (Y/N)', 'N/A')}")

        else:
            st.error(f"Part Number **{pn_input}** not found in the database.")
            st.info("You can add this part number in the 'Database Management' tab")

    elif not pn_input:
        st.info("""
        **Enter a Part Number** to analyze the supply chain risk.

        The system will calculate:
        - Geopolitical risk frontend/backend
        - Technology node risk
        - Switching cost (SW porting + qualification + certification)
        - Buffer stock coverage
        - Functional dependencies
        - Compatible alternatives with compatibility score
        """)


def _render_alternatives_table(alternatives: list) -> None:
    """Renderizza la tabella delle alternative consigliate con colori."""
    import pandas as pd

    _AVAIL_COLORS = {
        'Available': '🟢',
        'Tight':     '🟡',
        'Shortage':  '🔴',
        'Critical':  '🔴',
        'EOL':       '⚫',
    }

    rows = []
    for alt in alternatives:
        score = alt['compat_score']
        bar = '█' * int(score * 8) + '░' * (8 - int(score * 8))
        iface_flag = (
            '✅' if alt['interface_exact'] else
            '⚠️' if alt['interface_family'] else
            '—'
        )
        avail = alt.get('availability') or alt.get('market_severity', '')
        avail_icon = _AVAIL_COLORS.get(avail, '❓')
        rows.append({
            'Supplier':        alt['supplier'],
            'Compat.':         f"{bar} {score:.2f}",
            'Interface':       f"{iface_flag} {alt['interface_type']}",
            'Drop-In':         alt['drop_in'],
            'Porting (h)':     alt['porting_hours'] if alt['porting_hours'] else '—',
            'Availability':    f"{avail_icon} {avail}" if avail else '—',
            'Qualification':   alt['qualification'],
            'LT (wk)':         alt['lead_time_weeks'] if alt['lead_time_weeks'] else '—',
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


