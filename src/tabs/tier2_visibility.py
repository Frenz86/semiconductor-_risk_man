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
    """Tab: Tier-2/3 Supply Chain Visibility"""
    st.header("Tier-2/3 Supply Chain Visibility")
    st.markdown("""
    Analysis of upstream dependencies from Tier-1 suppliers: critical materials
    (gases, wafers, chemicals, substrates) and geographic concentration of Tier-2/3 suppliers.

    **Hybrid approach**: predefined mappings based on category/technology node
    + ability to customize with specific data.
    """)

    batch = st.session_state.get('batch_results')
    if not batch:
        st.info("Run a **Multiple Analysis** first to analyze Tier-2/3 dependencies.")
        return

    components_data = batch['components_data']
    components_risk = batch['components_risk']

    # Load custom data from database
    db = st.session_state.db
    all_custom_materials = db.get_all_component_materials()

    # =========================================================================
    # SECTION 1: BOM BOTTLENECK SUMMARY
    # =========================================================================
    st.subheader("BOM-Level Bottleneck Analysis")

    bom_analysis = analyze_bom_tier2_bottlenecks(components_data, all_custom_materials)

    # KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Unique Critical Materials", len(bom_analysis['top_bottlenecks']))
    with col2:
        st.metric("Average Tier-2 Score", f"{bom_analysis['bom_tier2_score']:.1f}/25")
    with col3:
        country_conc = bom_analysis.get('country_concentration', {})
        if country_conc:
            top_country = max(country_conc, key=lambda c: country_conc[c]['total_exposure'])
            st.metric("Most Exposed Country", top_country.title())
        else:
            st.metric("Most Exposed Country", "N/A")
    with col4:
        high_t2 = sum(
            1 for r in components_risk
            if r.get('tier2_risk', {}).get('tier2_score', 0) > 15
        )
        st.metric("High T2 Risk Components", high_t2)

    # Top bottlenecks table
    if bom_analysis['top_bottlenecks']:
        bottleneck_rows = []
        for b in bom_analysis['top_bottlenecks'][:10]:
            bottleneck_rows.append({
                'Material': b['name'],
                'Category': b['category'],
                'Dependent Components': b['affected_count'],
                'Max Concentration': f"{b['max_concentration']:.0%}",
                'Dominant Country': b['dominant_country'].title(),
                'Criticality': b['criticality'],
                'Substitutability': b['substitutability'],
            })
        st.dataframe(pd.DataFrame(bottleneck_rows), use_container_width=True, hide_index=True)

    # =========================================================================
    # SECTION 2: CONCENTRATION HEATMAP BY COUNTRY
    # =========================================================================
    st.subheader("Material Concentration Heatmap by Country")

    heatmap_data = bom_analysis.get('heatmap_data', [])
    if heatmap_data:
        df_heat = pd.DataFrame(heatmap_data)
        pivot = df_heat.pivot(index='Material', columns='Country', values='Exposure').fillna(0)

        if not pivot.empty:
            fig_heat = px.imshow(
                pivot,
                color_continuous_scale=['#e8f5e9', '#ffbb33', '#ff4444'],
                labels={'color': 'Exposure'},
                title="Tier-2/3 Dependency Concentration by Country",
                aspect='auto',
            )
            fig_heat.update_layout(height=max(400, len(pivot) * 30))
            st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No data available for the heatmap.")

    # =========================================================================
    # SECTION 3: DETAIL BY COMPONENT
    # =========================================================================
    st.subheader("Tier-2 Dependencies by Component")

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
            f"{len(tier2.get('materials', []))} materials{custom_label}",
            expanded=(tier2_score > 15)
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Required Materials:**")
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
                    st.markdown("**Risk Factors:**")
                    for f in tier2['factors']:
                        st.markdown(f"- {f}")
                if tier2.get('suggestions'):
                    st.markdown("**Suggestions:**")
                    for s in tier2['suggestions']:
                        st.markdown(f"- {s}")

    # =========================================================================
    # SECTION 4: CUSTOM TIER-2 SUPPLIER MANAGEMENT
    # =========================================================================
    st.markdown("---")
    st.subheader("Custom Tier-2 Supplier and Material Management")

    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "Add Tier-2 Supplier",
        "View Suppliers",
        "Assign Material to PN"
    ])

    with sub_tab1:
        with st.form("add_tier2_supplier_form"):
            col1, col2 = st.columns(2)
            with col1:
                t2_name = st.text_input("Tier-2 Supplier Name *", key="t2_name")
                t2_material_type = st.text_input("Material Type *", key="t2_mat_type")
                material_keys_options = list(MATERIAL_DATABASE.keys()) + ["__custom__"]
                t2_material_key = st.selectbox(
                    "Material Key (predefined or custom)",
                    options=material_keys_options,
                    key="t2_mat_key"
                )
            with col2:
                t2_country = st.text_input("Country *", key="t2_country")
                t2_share = st.number_input("Market Share (%)", 0, 100, 10, key="t2_share")
                t2_criticality = st.selectbox(
                    "Criticality",
                    ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                    key="t2_crit"
                )
                t2_substitutability = st.selectbox(
                    "Substitutability",
                    ["HIGH", "MEDIUM", "LOW", "VERY_LOW"],
                    key="t2_subst"
                )

            t2_notes = st.text_area("Notes", key="t2_notes")

            if st.form_submit_button("Save Tier-2 Supplier", type="primary"):
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
                        st.success(f"Tier-2 supplier '{t2_name}' saved successfully!")
                        st.rerun()
                    else:
                        st.error("Error saving supplier.")
                else:
                    st.warning("Please fill in all required fields (*).")

    with sub_tab2:
        suppliers = db.get_tier2_suppliers()
        if suppliers:
            df_suppliers = pd.DataFrame(suppliers)
            st.dataframe(df_suppliers, use_container_width=True, hide_index=True)

            # Remove supplier
            supplier_ids = [s.get('Tier2_Supplier_ID', '') for s in suppliers]
            supplier_labels = [
                f"{s.get('Tier2_Supplier_ID', '')} - {s.get('Tier2_Supplier_Name', '')}"
                for s in suppliers
            ]
            selected_to_remove = st.selectbox(
                "Select supplier to remove",
                options=supplier_labels,
                key="t2_remove_select"
            )
            if st.button("Remove Supplier", key="t2_remove_btn"):
                idx = supplier_labels.index(selected_to_remove)
                sid = supplier_ids[idx]
                if db.remove_tier2_supplier(sid):
                    st.success(f"Supplier {sid} removed.")
                    st.rerun()
        else:
            st.info("No custom Tier-2 suppliers in the database.")

    with sub_tab3:
        all_pns = db.get_all_part_numbers()
        if all_pns:
            with st.form("assign_material_form"):
                selected_pn = st.selectbox("Part Number", options=all_pns, key="assign_pn")
                material_keys_list = list(MATERIAL_DATABASE.keys())
                selected_material = st.selectbox(
                    "Material",
                    options=material_keys_list,
                    format_func=lambda k: f"{k} - {MATERIAL_DATABASE[k]['name']}",
                    key="assign_mat"
                )
                custom_concentration = st.slider(
                    "Custom Concentration (%)", 0, 100, 50, key="assign_conc"
                )
                custom_country = st.text_input(
                    "Custom Country (override)", key="assign_country"
                )
                assign_notes = st.text_area("Notes", key="assign_notes")

                if st.form_submit_button("Assign Material", type="primary"):
                    mat_info = MATERIAL_DATABASE.get(selected_material, {})
                    success = db.add_component_material(selected_pn, {
                        'Material_Key': selected_material,
                        'Material_Name': mat_info.get('name', selected_material),
                        'Custom_Concentration': custom_concentration / 100.0,
                        'Custom_Country': custom_country,
                        'Notes': assign_notes,
                    })
                    if success:
                        st.success(f"Material '{selected_material}' assigned to {selected_pn}!")
                        st.rerun()
                    else:
                        st.error("Error assigning material.")

            # Show existing associations
            st.markdown("---")
            st.markdown("**Existing associations:**")
            if all_custom_materials:
                rows = []
                for pn, mats in all_custom_materials.items():
                    for m in mats:
                        rows.append({
                            'Part Number': pn,
                            'Material': m.get('Material_Name', m.get('Material_Key', '')),
                            'Concentration': f"{float(m.get('Custom_Concentration', 0)) * 100:.0f}%"
                                if m.get('Custom_Concentration') else 'Default',
                            'Country': m.get('Custom_Country', 'Default'),
                        })
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No custom associations.")
            else:
                st.info("No custom associations.")
        else:
            st.warning("No Part Numbers in the database.")

    # =========================================================================
    # SECTION 5: MITIGATION RECOMMENDATIONS
    # =========================================================================
    st.markdown("---")
    st.subheader("Tier-2/3 Mitigation Recommendations")

    recommendations = bom_analysis.get('recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"{i}. {rec}")
    else:
        st.info("No specific recommendations at this time.")


# =============================================================================

