"""
filiera_commerciale.py — Tab: render_tab_filiera_commerciale
"""

from distributor_risk import analyze_bom_distributor_risk, simulate_distributor_stockout
from ems_risk import analyze_bom_ems_risk
import pandas as pd
import streamlit as st


def render_tab_filiera_commerciale():
    """Tab Filiera Commerciale: EMS risk, Distributor risk, Hidden Single Source."""
    st.header("Filiera Commerciale")
    st.markdown(
        "Analisi del canale distributivo e del terzista EMS — livelli nascosti della supply chain."
    )

    batch = st.session_state.batch_results
    if not batch:
        st.info("Esegui prima un'**Analisi Multipla** (Tab 2) per caricare i dati della BOM.")
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

    tab_ems, tab_dist, tab_spof, tab_sim = st.tabs([
        "EMS Risk", "Distributori", "Hidden Single Source", "Simulatore Stock-Out"
    ])

    # =========================================================================
    # SUB-TAB: EMS RISK
    # =========================================================================
    with tab_ems:
        st.subheader("Rischio EMS (Electronics Manufacturing Services)")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Componenti via EMS", ems_analysis['ems_components_count'])
        with col2:
            st.metric("Score Medio EMS", f"{ems_analysis['avg_ems_score']:.1f}/30")
        with col3:
            st.metric("Componenti Critici EMS", len(ems_analysis['critical_ems']))

        st.markdown("---")

        # Tabella componenti con EMS
        ems_rows = []
        for r in ems_analysis['components_ems']:
            if r['ems_used']:
                ems_rows.append({
                    'Part Number': r.get('part_number', ''),
                    'EMS': r.get('ems_name', 'N/A'),
                    'Paese': r.get('ems_country', 'N/A'),
                    'Score EMS': r.get('ems_score', 0),
                    'Livello': r.get('ems_level', 'N/A'),
                    'Profilo': 'Sì' if r.get('has_profile') else 'Stima',
                })
        if ems_rows:
            df_ems = pd.DataFrame(ems_rows).sort_values('Score EMS', ascending=False)
            def _color_ems(row):
                score = row['Score EMS']
                if score >= 20:
                    return ['background-color: #ff444433'] * len(row)
                elif score >= 12:
                    return ['background-color: #ffbb3333'] * len(row)
                return [''] * len(row)
            st.dataframe(df_ems.style.apply(_color_ems, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("Nessun componente usa EMS (o campo EMS_Used non impostato)")

        if ems_analysis['shared_ems_risks']:
            st.markdown("---")
            st.subheader("EMS Condivisi (SPOF Potenziale)")
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
        st.subheader("Rischio Distributore")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Componenti con Distributore", len([r for r in dist_analysis['components_distributor'] if r['has_distributors']]))
        with col2:
            st.metric("Score Medio Distributore", f"{dist_analysis['avg_distributor_score']:.1f}/25")
        with col3:
            st.metric("Mono-Distributore", len(dist_analysis['mono_distributor_pns']))
        with col4:
            st.metric("Senza Distributore", len(dist_analysis['no_distributor_pns']))

        st.markdown("---")

        # Tabella
        dist_rows = []
        for r in dist_analysis['components_distributor']:
            dist_rows.append({
                'Part Number': r.get('part_number', ''),
                'Distributore Primario': r.get('primary_distributor', 'N/A'),
                'N. Distributori': r.get('distributor_count', 0),
                'Score': r.get('distributor_score', 0),
                'Livello': r.get('distributor_level', 'N/A') if r.get('has_distributors') else '—',
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
            st.subheader("Distributori Condivisi (SPOF Potenziale)")
            for shared in dist_analysis['top_shared_distributors']:
                icon = "🔴 SPOF" if shared['is_spof'] else "🟡"
                st.warning(
                    f"{icon} **{shared['distributor']}** → {shared['affected_count']} PN: "
                    f"{', '.join(shared['affected_pns'][:6])}"
                )

        if dist_analysis['no_distributor_pns']:
            st.markdown("---")
            st.info(
                f"**{len(dist_analysis['no_distributor_pns'])} PN senza distributore registrato**: "
                + ", ".join(dist_analysis['no_distributor_pns'][:8])
                + (" …" if len(dist_analysis['no_distributor_pns']) > 8 else "")
            )

    # =========================================================================
    # SUB-TAB: HIDDEN SINGLE SOURCE
    # =========================================================================
    with tab_spof:
        st.subheader("Hidden Single Source Detection")
        st.markdown("""
        Un componente ha **hidden single source** quando tutte le sue fonti alternative
        (inclusa la primaria) convergono sullo stesso paese di fabbricazione frontend.
        Avere 3 fornitori tutti con fab in Taiwan non diversifica il rischio geopolitico.
        """)

        hidden_components = [
            r for r in components_risk
            if r.get('hidden_single_source', {}).get('hidden_spof_score', 0) >= 4
        ]

        if not hidden_components:
            st.success(
                "Nessun hidden single source rilevato nella BOM attuale. "
                "Aggiungi fonti alternative nel tab Gestione Database → Fonti Alternative "
                "per abilitare il rilevamento."
            )
        else:
            st.error(f"**{len(hidden_components)} componenti con hidden single source**")

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
                    - **Paese convergente:** {overlap_country}
                    - **Fonti su quel paese:** {overlap_count} di {total_sources}
                    - **Livello:** {level}
                    - **Suggerimento:** Qualificare un fornitore alternativo con fab in paese diverso da {overlap_country}
                    """)

        st.markdown("---")
        st.subheader("Tutte le Fonti Alternative Registrate")
        all_alt = db.get_all_alt_sources()
        if all_alt:
            rows = []
            for pn_key, sources in all_alt.items():
                for s in sources:
                    rows.append({'Part Number': pn_key, **{k: v for k, v in s.items() if k != 'Part_Number'}})
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info(
                "Nessuna fonte alternativa nel DB. "
                "Aggiungile in Gestione Database → Fonti Alternative per attivare il rilevamento."
            )

    # =========================================================================
    # SUB-TAB: SIMULATORE STOCK-OUT DISTRIBUTORE
    # =========================================================================
    with tab_sim:
        st.subheader("Simulatore Stock-Out Distributore")
        st.markdown(
            "Simula l'impatto di uno stock-out su un distributore specifico: "
            "quali componenti restano scoperti e per quante settimane."
        )

        # Ottieni lista distributori dalla BOM corrente
        active_distributors = set()
        for r in dist_analysis['components_distributor']:
            if r.get('has_distributors') and r.get('primary_distributor') != 'N/A':
                active_distributors.add(r['primary_distributor'])

        if not active_distributors:
            st.info("Nessun distributore associato alla BOM. Aggiungi distribuzioni in Gestione Database → Distributori.")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            target_dist = st.selectbox("Distributore da simulare", sorted(active_distributors))
        with col2:
            stockout_weeks = st.slider("Settimane di stock-out", 1, 26, 4)
        with col3:
            sim_run_rate = st.number_input(
                "Run Rate (PCB/sett.)", min_value=1, value=st.session_state.run_rate
            )

        if st.button("Esegui Simulazione", type="primary"):
            sim_result = simulate_distributor_stockout(
                components_data, all_part_distributors,
                target_dist, stockout_weeks, sim_run_rate
            )

            summary = sim_result['summary']
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Componenti Impattati", summary['total_affected'])
            with col2:
                st.metric("Componenti Critici", summary['total_critical'], help="Buffer esaurito prima della fine dello stock-out")
            with col3:
                st.metric("Settimane Perse (media)", f"{summary['avg_weeks_lost']:.1f}")

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
                st.success(f"Nessun componente impattato da uno stock-out di {target_dist}")

