"""
tier2_visibility.py — Tab: render_tab_tier2_visibility
"""

from tier2_visibility import (
    calculate_tier2_risk,
    analyze_bom_tier2_bottlenecks,
    calculate_ip_risk,
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

    # =========================================================================
    # SECTION 6: IP/SW DEPENDENCIES (v4.1)
    # =========================================================================
    st.markdown("---")
    st.subheader("IP/SW Dependencies")

    db = st.session_state.db
    all_ip_deps = db.get_all_ip_dependencies()

    if not all_ip_deps:
        st.info("No IP dependencies tracked. Go to Database Management to add them.")
    else:
        # Aggrega IP deps per componente
        components = batch['components_data']
        ip_stats = {}
        critical_ips = []

        for comp in components:
            pn = str(comp.get('Part Number', '')).upper()
            ip_list = all_ip_deps.get(pn, [])

            if ip_list:
                ip_result = calculate_ip_risk(pn, ip_list)
                ip_stats[pn] = ip_result

                # Raccogli IP critici
                if ip_result.get('has_risk'):
                    for ip_dep in ip_list:
                        status = ip_dep.get('Maintenance_Status', 'Active')
                        if status in ['Abandoned', 'Deprecated']:
                            critical_ips.append({
                                'pn': pn,
                                'ip_name': ip_dep['IP_Name'],
                                'vendor': ip_dep['IP_Vendor'],
                                'status': status,
                            })

        # Alert per IP critici
        if critical_ips:
            st.error(f"⚠️ **{len(critical_ips)} Critical IP Issues Found**")
            for issue in critical_ips:
                status_emoji = "🚫" if issue['status'] == 'Abandoned' else "⚠️"
                st.markdown(
                    f"- {status_emoji} **{issue['status'].upper()}**: "
                    f"`{issue['ip_name']}` (by {issue['vendor']}) in PN `{issue['pn']}`"
                )

        # Tabella riepilogativa vendor IP
        st.markdown("**IP Vendor Risk Summary**")

        vendor_risk = {}
        for pn, ip_list in all_ip_deps.items():
            if any(c.get('Part Number', '').upper() == pn for c in components):
                for ip_dep in ip_list:
                    vendor = ip_dep['IP_Vendor']
                    if vendor not in vendor_risk:
                        vendor_risk[vendor] = {'count': 0, 'proprietary': 0, 'critical': 0}
                    vendor_risk[vendor]['count'] += 1
                    if ip_dep.get('License_Type') == 'Proprietary':
                        vendor_risk[vendor]['proprietary'] += 1
                    if ip_dep.get('Maintenance_Status') in ['Abandoned', 'Deprecated']:
                        vendor_risk[vendor]['critical'] += 1

        if vendor_risk:
            vendor_data = []
            for vendor, stats in sorted(vendor_risk.items(), key=lambda x: x[1]['critical'], reverse=True):
                vendor_data.append({
                    'IP Vendor': vendor,
                    'Total IPs': stats['count'],
                    'Proprietary': stats['proprietary'],
                    'Critical Issues': stats['critical'],
                })

            df_vendors = pd.DataFrame(vendor_data)
            st.dataframe(df_vendors, use_container_width=True, hide_index=True)

        # Dettaglio per componente con IP risk > 0
        st.markdown("**Components with IP Risk**")

        components_with_ip_risk = [pn for pn, result in ip_stats.items() if result.get('has_risk')]

        if components_with_ip_risk:
            for pn in sorted(components_with_ip_risk):
                ip_result = ip_stats[pn]
                ip_score = ip_result.get('ip_score', 0)

                # Colore dell'expander basato su score
                if ip_score >= 15:
                    risk_color = "🔴"
                elif ip_score >= 8:
                    risk_color = "🟠"
                else:
                    risk_color = "🟡"

                with st.expander(f"{risk_color} **{pn}** (IP Risk: {ip_score}/20)"):
                    ip_list = all_ip_deps.get(pn, [])

                    # Mostra lista IP deps
                    for ip_dep in ip_list:
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.markdown(f"**{ip_dep['IP_Name']}**")
                            st.caption(f"by {ip_dep['IP_Vendor']}")
                        with col2:
                            lic = ip_dep.get('License_Type', 'N/A')
                            status = ip_dep.get('Maintenance_Status', 'Active')
                            st.markdown(f"*{lic}*")
                            st.caption(f"Status: {status}")
                        with col3:
                            alts = int(ip_dep.get('Vendor_Alternatives', 0))
                            if alts == 0:
                                st.error(f"0 alt")
                            elif alts == 1:
                                st.warning(f"{alts} alt")
                            else:
                                st.success(f"{alts} alt")

                    # Mostra fattori
                    if ip_result.get('ip_factors'):
                        st.markdown("**Risk Factors:**")
                        for factor in ip_result['ip_factors']:
                            st.markdown(f"- {factor}")

                    # Mostra suggerimenti
                    if ip_result.get('ip_suggestions'):
                        st.markdown("**Mitigation Actions:**")
                        for sugg in ip_result['ip_suggestions']:
                            st.markdown(f"- {sugg}")
        else:
            st.success("✅ No IP dependency risks detected in this BOM.")


# =============================================================================

