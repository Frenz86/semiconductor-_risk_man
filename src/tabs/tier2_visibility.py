"""
tier2_visibility.py — Tab: render_tab_tier2_visibility
"""

from tier2_visibility import (
    calculate_tier2_risk,
    analyze_bom_tier2_bottlenecks,
    MATERIAL_DATABASE,
    CATEGORY_MATERIAL_MAPPINGS,
)
import pandas as pd
import plotly.express as px
import streamlit as st


def render_tab_tier2_visibility():
    """Tab: Visibilita' Tier-2/3 Supply Chain"""
    st.header("Visibilita' Tier-2/3 Supply Chain")
    st.markdown("""
    Analisi delle dipendenze a monte dei fornitori Tier-1: materiali critici
    (gas, wafer, chimici, substrati) e concentrazione geografica dei fornitori Tier-2/3.

    **Approccio ibrido**: mappature predefinite basate su categoria/nodo tecnologico
    + possibilita' di personalizzare con dati specifici.
    """)

    batch = st.session_state.get('batch_results')
    if not batch:
        st.info("Esegui prima un'**Analisi Multipla** per analizzare le dipendenze Tier-2/3.")
        return

    components_data = batch['components_data']
    components_risk = batch['components_risk']

    # Carica dati custom dal database
    db = st.session_state.db
    all_custom_materials = db.get_all_component_materials()

    # =========================================================================
    # SEZIONE 1: SOMMARIO BOTTLENECK BOM
    # =========================================================================
    st.subheader("Analisi Bottleneck a Livello BOM")

    bom_analysis = analyze_bom_tier2_bottlenecks(components_data, all_custom_materials)

    # KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Materiali Critici Unici", len(bom_analysis['top_bottlenecks']))
    with col2:
        st.metric("Score Tier-2 Medio", f"{bom_analysis['bom_tier2_score']:.1f}/25")
    with col3:
        country_conc = bom_analysis.get('country_concentration', {})
        if country_conc:
            top_country = max(country_conc, key=lambda c: country_conc[c]['total_exposure'])
            st.metric("Paese Piu' Esposto", top_country.title())
        else:
            st.metric("Paese Piu' Esposto", "N/A")
    with col4:
        high_t2 = sum(
            1 for r in components_risk
            if r.get('tier2_risk', {}).get('tier2_score', 0) > 15
        )
        st.metric("Componenti Alto Rischio T2", high_t2)

    # Tabella top bottlenecks
    if bom_analysis['top_bottlenecks']:
        bottleneck_rows = []
        for b in bom_analysis['top_bottlenecks'][:10]:
            bottleneck_rows.append({
                'Materiale': b['name'],
                'Categoria': b['category'],
                'Componenti Dipendenti': b['affected_count'],
                'Max Concentrazione': f"{b['max_concentration']:.0%}",
                'Paese Dominante': b['dominant_country'].title(),
                'Criticita\'': b['criticality'],
                'Sostituibilita\'': b['substitutability'],
            })
        st.dataframe(pd.DataFrame(bottleneck_rows), use_container_width=True, hide_index=True)

    # =========================================================================
    # SEZIONE 2: HEATMAP CONCENTRAZIONE PER PAESE
    # =========================================================================
    st.subheader("Heatmap Concentrazione Materiali per Paese")

    heatmap_data = bom_analysis.get('heatmap_data', [])
    if heatmap_data:
        df_heat = pd.DataFrame(heatmap_data)
        pivot = df_heat.pivot(index='Material', columns='Country', values='Exposure').fillna(0)

        if not pivot.empty:
            fig_heat = px.imshow(
                pivot,
                color_continuous_scale=['#e8f5e9', '#ffbb33', '#ff4444'],
                labels={'color': 'Esposizione'},
                title="Concentrazione Dipendenze Tier-2/3 per Paese",
                aspect='auto',
            )
            fig_heat.update_layout(height=max(400, len(pivot) * 30))
            st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Nessun dato per la heatmap.")

    # =========================================================================
    # SEZIONE 3: DETTAGLIO PER COMPONENTE
    # =========================================================================
    st.subheader("Dipendenze Tier-2 per Componente")

    comp_tier2 = bom_analysis.get('component_tier2_risks', {})

    for risk in sorted(
        components_risk,
        key=lambda x: x.get('tier2_risk', {}).get('tier2_score', 0),
        reverse=True
    ):
        pn = risk.get('part_number', 'N/A')
        tier2 = comp_tier2.get(pn, risk.get('tier2_risk', {}))
        tier2_score = tier2.get('tier2_score', 0)
        color_emoji = "🔴" if tier2_score > 15 else "🟡" if tier2_score > 8 else "🟢"

        custom_count = len(all_custom_materials.get(pn, []))
        custom_label = f" + {custom_count} custom" if custom_count > 0 else ""

        with st.expander(
            f"{color_emoji} **{pn}** | T2 Score: {tier2_score}/25 | "
            f"{len(tier2.get('materials', []))} materiali{custom_label}",
            expanded=(tier2_score > 15)
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Materiali Richiesti:**")
                for mat in tier2.get('materials', []):
                    conc_pct = mat.get('concentration_risk', 0) * 100
                    icon = "🔴" if conc_pct > 60 else "🟡" if conc_pct > 30 else "🟢"
                    custom_tag = " *(custom)*" if mat.get('is_custom_override') else ""
                    st.markdown(
                        f"- {icon} **{mat['name']}** - "
                        f"{mat.get('dominant_country', 'N/A').title()} ({conc_pct:.0f}%)"
                        f"{custom_tag}"
                    )

            with col2:
                if tier2.get('factors'):
                    st.markdown("**Fattori di Rischio:**")
                    for f in tier2['factors']:
                        st.markdown(f"- {f}")
                if tier2.get('suggestions'):
                    st.markdown("**Suggerimenti:**")
                    for s in tier2['suggestions']:
                        st.markdown(f"- {s}")

    # =========================================================================
    # SEZIONE 4: GESTIONE FORNITORI TIER-2 CUSTOM
    # =========================================================================
    st.markdown("---")
    st.subheader("Gestione Fornitori e Materiali Tier-2 Custom")

    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "Aggiungi Fornitore Tier-2",
        "Visualizza Fornitori",
        "Associa Materiale a PN"
    ])

    with sub_tab1:
        with st.form("add_tier2_supplier_form"):
            col1, col2 = st.columns(2)
            with col1:
                t2_name = st.text_input("Nome Fornitore Tier-2 *", key="t2_name")
                t2_material_type = st.text_input("Tipo Materiale *", key="t2_mat_type")
                material_keys_options = list(MATERIAL_DATABASE.keys()) + ["__custom__"]
                t2_material_key = st.selectbox(
                    "Material Key (predefinito o custom)",
                    options=material_keys_options,
                    key="t2_mat_key"
                )
            with col2:
                t2_country = st.text_input("Paese *", key="t2_country")
                t2_share = st.number_input("Market Share (%)", 0, 100, 10, key="t2_share")
                t2_criticality = st.selectbox(
                    "Criticita'",
                    ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                    key="t2_crit"
                )
                t2_substitutability = st.selectbox(
                    "Sostituibilita'",
                    ["HIGH", "MEDIUM", "LOW", "VERY_LOW"],
                    key="t2_subst"
                )

            t2_notes = st.text_area("Note", key="t2_notes")

            if st.form_submit_button("Salva Fornitore Tier-2", type="primary"):
                if t2_name and t2_material_type and t2_country:
                    success = db.add_tier2_supplier({
                        'Tier2_Supplier_Name': t2_name,
                        'Material_Type': t2_material_type,
                        'Material_Key': t2_material_key if t2_material_key != "__custom__" else t2_material_type.lower().replace(' ', '_'),
                        'Country': t2_country,
                        'Market_Share_Pct': t2_share,
                        'Criticality': t2_criticality,
                        'Substitutability': t2_substitutability,
                        'Notes': t2_notes,
                    })
                    if success:
                        st.success(f"Fornitore Tier-2 '{t2_name}' salvato con successo!")
                        st.rerun()
                    else:
                        st.error("Errore nel salvataggio.")
                else:
                    st.warning("Compila tutti i campi obbligatori (*).")

    with sub_tab2:
        suppliers = db.get_tier2_suppliers()
        if suppliers:
            df_suppliers = pd.DataFrame(suppliers)
            st.dataframe(df_suppliers, use_container_width=True, hide_index=True)

            # Rimozione fornitore
            supplier_ids = [s.get('Tier2_Supplier_ID', '') for s in suppliers]
            supplier_labels = [
                f"{s.get('Tier2_Supplier_ID', '')} - {s.get('Tier2_Supplier_Name', '')}"
                for s in suppliers
            ]
            selected_to_remove = st.selectbox(
                "Seleziona fornitore da rimuovere",
                options=supplier_labels,
                key="t2_remove_select"
            )
            if st.button("Rimuovi Fornitore", key="t2_remove_btn"):
                idx = supplier_labels.index(selected_to_remove)
                sid = supplier_ids[idx]
                if db.remove_tier2_supplier(sid):
                    st.success(f"Fornitore {sid} rimosso.")
                    st.rerun()
        else:
            st.info("Nessun fornitore Tier-2 custom nel database.")

    with sub_tab3:
        all_pns = db.get_all_part_numbers()
        if all_pns:
            with st.form("assign_material_form"):
                selected_pn = st.selectbox("Part Number", options=all_pns, key="assign_pn")
                material_keys_list = list(MATERIAL_DATABASE.keys())
                selected_material = st.selectbox(
                    "Materiale",
                    options=material_keys_list,
                    format_func=lambda k: f"{k} - {MATERIAL_DATABASE[k]['name']}",
                    key="assign_mat"
                )
                custom_concentration = st.slider(
                    "Concentrazione Custom (%)", 0, 100, 50, key="assign_conc"
                )
                custom_country = st.text_input(
                    "Paese Custom (override)", key="assign_country"
                )
                assign_notes = st.text_area("Note", key="assign_notes")

                if st.form_submit_button("Associa Materiale", type="primary"):
                    mat_info = MATERIAL_DATABASE.get(selected_material, {})
                    success = db.add_component_material(selected_pn, {
                        'Material_Key': selected_material,
                        'Material_Name': mat_info.get('name', selected_material),
                        'Custom_Concentration': custom_concentration / 100.0,
                        'Custom_Country': custom_country,
                        'Notes': assign_notes,
                    })
                    if success:
                        st.success(f"Materiale '{selected_material}' associato a {selected_pn}!")
                        st.rerun()
                    else:
                        st.error("Errore nell'associazione.")

            # Mostra associazioni esistenti
            st.markdown("---")
            st.markdown("**Associazioni esistenti:**")
            if all_custom_materials:
                rows = []
                for pn, mats in all_custom_materials.items():
                    for m in mats:
                        rows.append({
                            'Part Number': pn,
                            'Materiale': m.get('Material_Name', m.get('Material_Key', '')),
                            'Concentrazione': f"{float(m.get('Custom_Concentration', 0)) * 100:.0f}%"
                                if m.get('Custom_Concentration') else 'Default',
                            'Paese': m.get('Custom_Country', 'Default'),
                        })
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Nessuna associazione custom.")
            else:
                st.info("Nessuna associazione custom.")
        else:
            st.warning("Nessun Part Number nel database.")

    # =========================================================================
    # SEZIONE 5: RACCOMANDAZIONI DI MITIGAZIONE
    # =========================================================================
    st.markdown("---")
    st.subheader("Raccomandazioni di Mitigazione Tier-2/3")

    recommendations = bom_analysis.get('recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"{i}. {rec}")
    else:
        st.info("Nessuna raccomandazione specifica al momento.")


# =============================================================================

