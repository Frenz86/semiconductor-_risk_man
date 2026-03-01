"""
filiera_commerciale.py — Tab: render_tab_filiera_commerciale
"""

from alternative_engine import find_compatible_alternatives, check_shortage_impact
from distributor_risk import analyze_bom_distributor_risk, simulate_distributor_stockout
from ems_risk import analyze_bom_ems_risk
import pandas as pd
import streamlit as st


def render_tab_filiera_commerciale():
    """Tab Filiera Commerciale: EMS risk, Distributor risk, Hidden Single Source."""
    st.header("Commercial Supply Chain")
    st.markdown(
        "Analysis of the distribution channel and EMS contract manufacturer — hidden layers of the supply chain."
    )

    batch = st.session_state.batch_results
    if not batch:
        st.info("Run a **Multiple Analysis** (Tab 2) first to load the BOM data.")
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

    tab_ems, tab_dist, tab_spof, tab_sim, tab_alt = st.tabs([
        "EMS Risk", "Distributors", "Hidden Single Source", "Stock-Out Simulator",
        "Smart Alternatives"
    ])

    # =========================================================================
    # SUB-TAB: EMS RISK
    # =========================================================================
    with tab_ems:
        st.subheader("EMS Risk (Electronics Manufacturing Services)")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Components via EMS", ems_analysis['ems_components_count'])
        with col2:
            st.metric("Avg EMS Score", f"{ems_analysis['avg_ems_score']:.1f}/30")
        with col3:
            st.metric("Critical EMS Components", len(ems_analysis['critical_ems']))

        st.markdown("---")

        # Tabella componenti con EMS
        ems_rows = []
        for r in ems_analysis['components_ems']:
            if r['ems_used']:
                ems_rows.append({
                    'Part Number': r.get('part_number', ''),
                    'EMS': r.get('ems_name', 'N/A'),
                    'Country': r.get('ems_country', 'N/A'),
                    'EMS Score': r.get('ems_score', 0),
                    'Level': r.get('ems_level', 'N/A'),
                    'Profile': 'Yes' if r.get('has_profile') else 'Estimated',
                })
        if ems_rows:
            df_ems = pd.DataFrame(ems_rows).sort_values('EMS Score', ascending=False)
            def _color_ems(row):
                score = row['EMS Score']
                if score >= 20:
                    return ['background-color: #ff444433'] * len(row)
                elif score >= 12:
                    return ['background-color: #ffbb3333'] * len(row)
                return [''] * len(row)
            st.dataframe(df_ems.style.apply(_color_ems, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("No component uses EMS (or EMS_Used field not set)")

        if ems_analysis['shared_ems_risks']:
            st.markdown("---")
            st.subheader("Shared EMS (Potential SPOF)")
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
        st.subheader("Distributor Risk")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Components with Distributor", len([r for r in dist_analysis['components_distributor'] if r['has_distributors']]))
        with col2:
            st.metric("Avg Distributor Score", f"{dist_analysis['avg_distributor_score']:.1f}/25")
        with col3:
            st.metric("Single-Distributor", len(dist_analysis['mono_distributor_pns']))
        with col4:
            st.metric("No Distributor", len(dist_analysis['no_distributor_pns']))

        st.markdown("---")

        # Tabella
        dist_rows = []
        for r in dist_analysis['components_distributor']:
            dist_rows.append({
                'Part Number': r.get('part_number', ''),
                'Primary Distributor': r.get('primary_distributor', 'N/A'),
                'No. Distributors': r.get('distributor_count', 0),
                'Score': r.get('distributor_score', 0),
                'Level': r.get('distributor_level', 'N/A') if r.get('has_distributors') else '—',
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
            st.subheader("Shared Distributors (Potential SPOF)")
            for shared in dist_analysis['top_shared_distributors']:
                icon = "🔴 SPOF" if shared['is_spof'] else "🟡"
                st.warning(
                    f"{icon} **{shared['distributor']}** → {shared['affected_count']} PN: "
                    f"{', '.join(shared['affected_pns'][:6])}"
                )

        if dist_analysis['no_distributor_pns']:
            st.markdown("---")
            st.info(
                f"**{len(dist_analysis['no_distributor_pns'])} PN with no registered distributor**: "
                + ", ".join(dist_analysis['no_distributor_pns'][:8])
                + (" …" if len(dist_analysis['no_distributor_pns']) > 8 else "")
            )

    # =========================================================================
    # SUB-TAB: HIDDEN SINGLE SOURCE
    # =========================================================================
    with tab_spof:
        st.subheader("Hidden Single Source Detection")
        st.markdown("""
        A component has a **hidden single source** when all its alternative sources
        (including the primary) converge on the same frontend manufacturing country.
        Having 3 suppliers all with fabs in Taiwan does not diversify geopolitical risk.
        """)

        hidden_components = [
            r for r in components_risk
            if r.get('hidden_single_source', {}).get('hidden_spof_score', 0) >= 4
        ]

        if not hidden_components:
            st.success(
                "No hidden single source detected in the current BOM. "
                "Add alternative sources in the Database Management tab → Alternative Sources "
                "to enable detection."
            )
        else:
            st.error(f"**{len(hidden_components)} components with hidden single source**")

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
                    - **Converging country:** {overlap_country}
                    - **Sources in that country:** {overlap_count} of {total_sources}
                    - **Level:** {level}
                    - **Recommendation:** Qualify an alternative supplier with a fab in a country other than {overlap_country}
                    """)

        st.markdown("---")
        st.subheader("All Registered Alternative Sources")
        all_alt = db.get_all_alt_sources()
        if all_alt:
            rows = []
            for pn_key, sources in all_alt.items():
                for s in sources:
                    rows.append({'Part Number': pn_key, **{k: v for k, v in s.items() if k != 'Part_Number'}})
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info(
                "No alternative sources in the DB. "
                "Add them in Database Management → Alternative Sources to enable detection."
            )

    # =========================================================================
    # SUB-TAB: SIMULATORE STOCK-OUT DISTRIBUTORE
    # =========================================================================
    with tab_sim:
        st.subheader("Distributor Stock-Out Simulator")
        st.markdown(
            "Simulate the impact of a stock-out on a specific distributor: "
            "which components are left uncovered and for how many weeks."
        )

        # Ottieni lista distributori dalla BOM corrente
        active_distributors = set()
        for r in dist_analysis['components_distributor']:
            if r.get('has_distributors') and r.get('primary_distributor') != 'N/A':
                active_distributors.add(r['primary_distributor'])

        if not active_distributors:
            st.info("No distributor associated with the BOM. Add distributors in Database Management → Distributors.")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            target_dist = st.selectbox("Distributor to simulate", sorted(active_distributors))
        with col2:
            stockout_weeks = st.slider("Stock-out weeks", 1, 26, 4)
        with col3:
            sim_run_rate = st.number_input(
                "Run Rate (PCB/week)", min_value=1, value=st.session_state.run_rate
            )

        if st.button("Run Simulation", type="primary"):
            sim_result = simulate_distributor_stockout(
                components_data, all_part_distributors,
                target_dist, stockout_weeks, sim_run_rate
            )

            summary = sim_result['summary']
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Impacted Components", summary['total_affected'])
            with col2:
                st.metric("Critical Components", summary['total_critical'], help="Buffer exhausted before the end of the stock-out")
            with col3:
                st.metric("Lost Weeks (avg)", f"{summary['avg_weeks_lost']:.1f}")

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
                st.success(f"No component impacted by a stock-out of {target_dist}")

    # =========================================================================
    # SUB-TAB: ALTERNATIVE INTELLIGENTI (v5.0)
    # =========================================================================
    with tab_alt:
        st.subheader("Smart Alternatives — Compatibility Graph")
        st.markdown(
            "Shows compatible alternatives for each component taking into account "
            "supported interfaces, market shortages and porting effort."
        )

        market_shortage = db.get_market_shortage()
        all_alt_sources = db.get_all_alt_sources()

        # Alert shortage globale
        if market_shortage:
            shortage_items = [f"**{k}** ({v})" for k, v in market_shortage.items() if v != 'Available']
            if shortage_items:
                st.error("⚠️ Active market shortages: " + " · ".join(shortage_items))

        # Selezione PN
        pn_list = [str(c.get('Part Number', '')) for c in components_data if c.get('Part Number')]
        if not pn_list:
            st.info("No components available.")
        else:
            selected_pn = st.selectbox("Select Part Number", pn_list, key="alt_pn_select")
            pn_data = next((c for c in components_data if str(c.get('Part Number', '')).upper() == selected_pn.upper()), {})
            alt_sources = all_alt_sources.get(selected_pn.upper(), [])

            # Info interfacce supportate dal PN
            supported = pn_data.get('Supported_Interfaces', '')
            if supported and str(supported) not in ('', 'nan'):
                st.info(f"Interfaces supported by **{selected_pn}**: `{supported}`")
            else:
                st.caption("The `Supported_Interfaces` field is not filled for this PN — add it in Database Management to enable compatibility matching.")

            # Shortage check per questo PN
            shortage_info = check_shortage_impact(pn_data, market_shortage)
            if shortage_info['affected']:
                ifaces = ', '.join(shortage_info['affected_interfaces'])
                st.warning(f"⚠️ This component uses **{ifaces}** — currently in **{shortage_info['severity']}** status")
                for note in shortage_info.get('shortage_notes', []):
                    st.caption(f"  • {note}")

            # Tabella alternative
            if alt_sources:
                alternatives = find_compatible_alternatives(selected_pn, pn_data, alt_sources, market_shortage)
                if alternatives:
                    st.markdown(f"**{len(alternatives)} alternative(s) found:**")
                    _render_alternatives_table_filiera(alternatives)
                else:
                    st.info("Alternatives present but no compatibility data. Fill in `Interface_Type` in Database Management.")
            else:
                st.info(f"No alternative source registered for **{selected_pn}**. Add them in Database Management → Alternative Sources.")

        # Panoramica shortage per tutta la BOM
        st.markdown("---")
        st.subheader("Shortage Overview — Full BOM")
        shortage_rows = []
        for comp in components_data:
            pn = str(comp.get('Part Number', ''))
            si = check_shortage_impact(comp, market_shortage)
            if si['affected']:
                shortage_rows.append({
                    'Part Number': pn,
                    'Affected Interfaces': ', '.join(si['affected_interfaces']),
                    'Severity': si['severity'],
                    'Available Alternatives': len(all_alt_sources.get(pn.upper(), [])),
                })
        if shortage_rows:
            df_sh = pd.DataFrame(shortage_rows).sort_values('Severity', ascending=False)
            def _color_severity(row):
                s = row['Severity']
                if s == 'Critical': return ['background-color: #ff444433'] * len(row)
                if s == 'Shortage': return ['background-color: #ff888833'] * len(row)
                if s == 'Tight':    return ['background-color: #ffbb3333'] * len(row)
                return [''] * len(row)
            st.dataframe(df_sh.style.apply(_color_severity, axis=1), use_container_width=True, hide_index=True)
        else:
            st.success("No BOM component is impacted by active market shortages.")


def _render_alternatives_table_filiera(alternatives: list) -> None:
    """Renderizza tabella alternative per la Filiera Commerciale."""
    _AVAIL_ICONS = {'Available': '🟢', 'Tight': '🟡', 'Shortage': '🔴', 'Critical': '🔴', 'EOL': '⚫'}
    rows = []
    for alt in alternatives:
        score = alt['compat_score']
        bar = '█' * int(score * 8) + '░' * (8 - int(score * 8))
        iface_flag = '✅' if alt['interface_exact'] else ('⚠️' if alt['interface_family'] else '—')
        avail = alt.get('availability') or alt.get('market_severity', '')
        avail_icon = _AVAIL_ICONS.get(avail, '❓')
        rows.append({
            'Supplier':      alt['supplier'],
            'Compat.':       f"{bar} {score:.2f}",
            'Interface':     f"{iface_flag} {alt['interface_type']}",
            'Drop-In':       alt['drop_in'],
            'Porting (h)':   alt['porting_hours'] if alt['porting_hours'] else '—',
            'Availability':  f"{avail_icon} {avail}" if avail else '—',
            'Fab Country':   alt['frontend_country'],
            'Qualification': alt['qualification'],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
