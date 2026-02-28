"""
gestione_database.py — Tab: render_tab_gestione_database
"""

import pandas as pd
import streamlit as st


def render_tab_gestione_database():
    """Tab 6: Gestione Database Part Numbers"""
    st.header("Gestione Database Part Numbers")

    tab6_1, tab6_2, tab6_3, tab6_ems, tab6_dist, tab6_alt, tab6_sup = st.tabs([
        "Statistiche", "Aggiungi Part Number", "Gestione Clienti",
        "EMS Providers", "Distributori", "Fonti Alternative", "Profili Fornitore"
    ])

    with tab6_1:
        st.subheader("Statistiche Database")

        stats = st.session_state.db.get_stats()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Part Numbers", stats['total_part_numbers'])
        with col2:
            st.metric("Clienti", stats['total_clients'])
        with col3:
            st.metric("EMS Providers", stats.get('total_ems_providers', 0))
        with col4:
            st.metric("Distributori", stats.get('total_distributors', 0))
        with col5:
            st.metric("Profili Fornitore", stats.get('total_supplier_profiles', 0))

        st.markdown("---")

        if stats['categories']:
            st.subheader("Part Numbers per Categoria")
            df_cat = pd.DataFrame(list(stats['categories'].items()), columns=['Categoria', 'Count'])
            st.bar_chart(df_cat.set_index('Categoria'))

        if stats['suppliers']:
            st.subheader("Top Fornitori")
            df_sup = pd.DataFrame(list(stats['suppliers'].items()), columns=['Fornitore', 'Count']).head(10)
            st.dataframe(df_sup, use_container_width=True)

    with tab6_2:
        st.subheader("Aggiungi Nuovo Part Number")

        with st.form("add_new_pn_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_pn = st.text_input("Part Number *")
                new_supplier = st.text_input("Supplier Name *")
                new_category = st.selectbox(
                    "Category *",
                    ["MCU", "MPU", "Sensor", "Analogic", "Power", "Passive Component", "Transceiver Wireless"]
                )

            with col2:
                price = st.number_input("Unit Price ($)", min_value=0.0, value=0.0, step=0.01)
                lead_time = st.number_input("Lead Time (weeks) *", min_value=0, value=8)
                weeks_qualify = st.number_input("Weeks to Qualify", min_value=0, value=12)

            st.markdown("#### Paesi Produzione")
            col1, col2 = st.columns(2)
            with col1:
                country1 = st.text_input("Plant 1 Country *")
                country2 = st.text_input("Plant 2 Country")
            with col2:
                country3 = st.text_input("Plant 3 Country")
                country4 = st.text_input("Plant 4 Country")

            st.markdown("#### Geo Risk Frontend/Backend (v3.0)")
            col1, col2, col3 = st.columns(3)
            with col1:
                frontend_country = st.text_input("Frontend Country (wafer fab)")
                backend_country = st.text_input("Backend Country (assembly/test)")
            with col2:
                tech_node = st.text_input("Technology Node (es. 28nm, 180nm)")
            with col3:
                ems_used = st.selectbox("EMS Used", ["N", "Y"])
                ems_name = st.text_input("EMS Name (se usato)")

            st.markdown("#### SW/Firmware (v3.0)")
            col1, col2, col3 = st.columns(3)
            with col1:
                sw_size = st.number_input("SW Code Size (KB)", min_value=0, value=0)
            with col2:
                os_type = st.selectbox("OS Type", ["Baremetal", "RTOS", "FreeRTOS", "Linux", "Android"])
            with col3:
                memory_type = st.selectbox("Memory Type", ["Embedded", "External"])

            st.markdown("#### Caratteristiche")
            col1, col2, col3 = st.columns(3)
            with col1:
                proprietary = st.selectbox("Proprietary", ["N", "Y"])
            with col2:
                commodity = st.selectbox("Commodity", ["Y", "N"])
            with col3:
                standalone = st.selectbox("Stand-Alone", ["Y", "N"])

            st.markdown("#### Dati Cliente")
            col1, col2 = st.columns(2)
            with col1:
                qty_bom = st.number_input("Qty in BOM", min_value=1, value=1)
            with col2:
                buffer_stock = st.number_input("Buffer Stock Units", min_value=0, value=0)

            certification = st.text_input("Certification/Qualification (optional)")
            dependency = st.text_input("Dependencies (optional)")

            submitted = st.form_submit_button("Salva Part Number", type="primary")

            if submitted:
                if not new_pn or not new_supplier or not country1:
                    st.error("Part Number, Supplier Name e almeno un paese sono obbligatori")
                else:
                    new_pn_data = {
                        'Supplier Name': new_supplier,
                        'Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)': new_category,
                        'Country of Manufacturing Plant 1': country1,
                        'Country of Manufacturing Plant 2': country2 or '',
                        'Country of Manufacturing Plant 3': country3 or '',
                        'Country of Manufacturing Plant 4': country4 or '',
                        'Supplier Lead Time (weeks)': lead_time,
                        'Unit Price ($)': price,
                        'Weeks to qualify': weeks_qualify,
                        'Proprietary (Y/N)**': proprietary,
                        'Commodity (Y/N)*': commodity,
                        'Stand-Alone Functional Device (Y/N)': standalone,
                        'How Many Device of this specific PN are in the BOM?': qty_bom,
                        'If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units': buffer_stock,
                        'Specify Certification/Qualification': certification or '',
                        'In case answer on Column C is Y, Which other device in the BOM is necessary to run the PN on Column B? (e.g. PMIC for MPU, Memory for MPU)': dependency or '',
                        'Frontend_Country': frontend_country or '',
                        'Backend_Country': backend_country or '',
                        'Technology_Node': tech_node or '',
                        'SW_Code_Size_KB': sw_size,
                        'OS_Type': os_type,
                        'Memory_Type': memory_type,
                        'EMS_Used': ems_used,
                        'EMS_Name': ems_name or '',
                    }

                    if st.session_state.db.add_part_number(new_pn, new_pn_data, st.session_state.current_client):
                        st.success(f"Part Number **{new_pn}** salvato con successo!")
                    else:
                        st.error("Errore nel salvataggio")

        st.markdown("---")
        st.subheader("Ricerca Part Numbers")
        search_pattern = st.text_input("Cerca per pattern")
        if search_pattern:
            results = st.session_state.db.search_similar(search_pattern)
            if results:
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.info("Nessun risultato")

    with tab6_3:
        st.subheader("Gestione Clienti")

        clients = st.session_state.db.get_all_clients()
        if clients:
            st.dataframe(pd.DataFrame(clients), use_container_width=True)

        st.markdown("---")
        st.subheader("Aggiungi Nuovo Cliente")

        with st.form("add_client_form"):
            new_client_id = st.text_input("Client ID *")
            new_client_name = st.text_input("Client Name *")
            new_client_run_rate = st.number_input("Default Run Rate", min_value=1, value=5000)

            submitted = st.form_submit_button("Aggiungi Cliente", type="primary")

            if submitted:
                if not new_client_id or not new_client_name:
                    st.error("Client ID e Client Name sono obbligatori")
                elif st.session_state.db.add_client(new_client_id, new_client_name, new_client_run_rate):
                    st.success(f"Cliente **{new_client_name}** aggiunto con successo!")
                    st.rerun()
                else:
                    st.error("Errore nell'aggiunta del cliente")

    # -------------------------------------------------------------------------
    # SUB-TAB: EMS PROVIDERS (v4.0)
    # -------------------------------------------------------------------------
    with tab6_ems:
        st.subheader("EMS Providers")
        st.markdown("Gestisci i profili dei terzisti EMS (Foxconn, Jabil, Flextronics, ecc.)")

        existing_ems = st.session_state.db.get_all_ems_providers()
        if existing_ems:
            st.dataframe(pd.DataFrame(existing_ems), use_container_width=True)

            st.markdown("**Rimuovi EMS Provider:**")
            ems_ids = [e.get('EMS_ID', '') for e in existing_ems]
            ems_to_del = st.selectbox("Seleziona EMS da rimuovere", options=[''] + ems_ids, key="ems_del_sel")
            if ems_to_del and st.button("Rimuovi EMS", key="ems_del_btn"):
                if st.session_state.db.remove_ems_provider(ems_to_del):
                    st.success("EMS rimosso")
                    st.rerun()

        st.markdown("---")
        st.subheader("Aggiungi / Aggiorna EMS Provider")

        with st.form("add_ems_form"):
            col1, col2 = st.columns(2)
            with col1:
                ems_name_f = st.text_input("EMS Name *", placeholder="es. Foxconn, Jabil, Flex")
                ems_country_f = st.text_input("Country *", placeholder="es. China, Malaysia")
                ems_fin_f = st.selectbox("Financial Health", ["A", "B", "C", "D"])
            with col2:
                ems_cap_f = st.slider("Capacity Utilization (%)", 0, 100, 75)
                ems_backup_f = st.number_input("Backup Sites Count", min_value=0, value=0)
                ems_years_f = st.number_input("Years in Business", min_value=0, value=10)
            ems_certs_f = st.text_input("Certifications (comma-sep.)", placeholder="ISO9001, IATF16949, AS9100")
            ems_notes_f = st.text_area("Note", height=60)

            if st.form_submit_button("Salva EMS Provider", type="primary"):
                if not ems_name_f or not ems_country_f:
                    st.error("Nome e Paese sono obbligatori")
                else:
                    data = {
                        'EMS_Name': ems_name_f,
                        'Country': ems_country_f,
                        'Financial_Health': ems_fin_f,
                        'Capacity_Utilization_Pct': ems_cap_f,
                        'Backup_Sites_Count': ems_backup_f,
                        'Years_Business': ems_years_f,
                        'Certifications': ems_certs_f,
                        'Notes': ems_notes_f,
                    }
                    if st.session_state.db.add_ems_provider(data):
                        st.success(f"EMS Provider **{ems_name_f}** salvato!")
                        st.rerun()
                    else:
                        st.error("Errore nel salvataggio")

    # -------------------------------------------------------------------------
    # SUB-TAB: DISTRIBUTORI (v4.0)
    # -------------------------------------------------------------------------
    with tab6_dist:
        st.subheader("Distributori")
        st.markdown("Gestisci distributori (Arrow, Avnet, TTI, Digi-Key, ecc.) e le loro associazioni ai Part Numbers.")

        existing_dists = st.session_state.db.get_all_distributors()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Distributori registrati:**")
            if existing_dists:
                st.dataframe(pd.DataFrame(existing_dists)[[
                    'Distributor_ID', 'Name', 'Country', 'Financial_Health',
                    'Lead_Time_Markup_Weeks', 'Stock_Level_Weeks_Coverage'
                ]], use_container_width=True)
            else:
                st.info("Nessun distributore registrato")

        with col2:
            st.markdown("**Aggiungi / Aggiorna Distributore:**")
            with st.form("add_dist_form"):
                dist_name_f = st.text_input("Nome *", placeholder="es. Arrow Electronics")
                dist_country_f = st.text_input("Paese *", placeholder="es. USA")
                dist_fin_f = st.selectbox("Financial Health", ["A", "B", "C", "D"])
                dist_markup_f = st.number_input("Lead Time Markup (settimane)", min_value=0, value=2)
                dist_stock_f = st.number_input("Stock Coverage (settimane medie)", min_value=0.0, value=4.0, step=0.5)
                dist_certs_f = st.text_input("Certificazioni", placeholder="AS9120, ISO9001")
                dist_backup_f = st.number_input("Backup Distributors Count", min_value=0, value=0)
                dist_notes_f = st.text_area("Note", height=60)

                if st.form_submit_button("Salva Distributore", type="primary"):
                    if not dist_name_f or not dist_country_f:
                        st.error("Nome e Paese obbligatori")
                    else:
                        d = {
                            'Name': dist_name_f, 'Country': dist_country_f,
                            'Financial_Health': dist_fin_f,
                            'Lead_Time_Markup_Weeks': dist_markup_f,
                            'Stock_Level_Weeks_Coverage': dist_stock_f,
                            'Certifications': dist_certs_f,
                            'Backup_Count': dist_backup_f,
                            'Notes': dist_notes_f,
                        }
                        if st.session_state.db.add_distributor(d):
                            st.success(f"Distributore **{dist_name_f}** salvato!")
                            st.rerun()
                        else:
                            st.error("Errore nel salvataggio")

        st.markdown("---")
        st.subheader("Associa Distributore a Part Number")

        if existing_dists:
            with st.form("add_pn_dist_form"):
                col1, col2 = st.columns(2)
                with col1:
                    pn_for_dist = st.text_input("Part Number *")
                    dist_options = {f"{d['Name']} ({d['Distributor_ID']})": d['Distributor_ID'] for d in existing_dists}
                    sel_dist_label = st.selectbox("Distributore *", options=list(dist_options.keys()))
                with col2:
                    dist_priority = st.selectbox("Priority", ["Primary", "Secondary"])
                    dist_alloc_pct = st.slider("Allocation %", 0, 100, 100)

                if st.form_submit_button("Associa", type="primary"):
                    if not pn_for_dist:
                        st.error("Part Number obbligatorio")
                    else:
                        if st.session_state.db.add_part_distributor(pn_for_dist, {
                            'Distributor_ID': dist_options[sel_dist_label],
                            'Priority': dist_priority,
                            'Allocation_Pct': dist_alloc_pct,
                        }):
                            st.success(f"Associato {sel_dist_label} a {pn_for_dist}")
                        else:
                            st.error("Errore")
        else:
            st.info("Aggiungi prima un distributore per poterlo associare a un Part Number")

    # -------------------------------------------------------------------------
    # SUB-TAB: FONTI ALTERNATIVE (v4.0)
    # -------------------------------------------------------------------------
    with tab6_alt:
        st.subheader("Fonti Alternative (Multi-sourcing)")
        st.markdown("""
        Registra le fonti alternative per ogni Part Number, **includendo il paese di fabbricazione**.
        Il sistema rileverà automaticamente se tutte le alternative convergono sullo stesso paese
        (hidden single source).
        """)

        with st.form("add_alt_source_form"):
            col1, col2 = st.columns(2)
            with col1:
                alt_pn = st.text_input("Part Number *")
                alt_supplier = st.text_input("Supplier Name *", placeholder="es. Infineon")
                alt_frontend = st.text_input("Frontend Country *", placeholder="es. Taiwan")
                alt_backend = st.text_input("Backend Country", placeholder="es. Malaysia")
            with col2:
                alt_lt = st.number_input("Lead Time (settimane)", min_value=0, value=12)
                alt_fin = st.selectbox("Financial Health", ["A", "B", "C", "D"])
                alt_qual = st.selectbox("Qualification Status", ["Qualified", "In_Progress", "Not_Started"])
                alt_alloc = st.slider("Allocation %", 0, 100, 0)
            alt_notes = st.text_area("Note", height=60)

            if st.form_submit_button("Aggiungi Fonte Alternativa", type="primary"):
                if not alt_pn or not alt_supplier or not alt_frontend:
                    st.error("Part Number, Supplier e Frontend Country sono obbligatori")
                else:
                    d = {
                        'Supplier_Name': alt_supplier,
                        'Frontend_Country': alt_frontend,
                        'Backend_Country': alt_backend,
                        'Lead_Time_Weeks': alt_lt,
                        'Financial_Health': alt_fin,
                        'Qualification_Status': alt_qual,
                        'Allocation_Pct': alt_alloc,
                        'Notes': alt_notes,
                    }
                    if st.session_state.db.add_alt_source(alt_pn, d):
                        st.success(f"Fonte alternativa aggiunta per {alt_pn}")
                        st.rerun()
                    else:
                        st.error("Errore nel salvataggio")

        st.markdown("---")
        st.subheader("Fonti Alternative Registrate")
        all_alt = st.session_state.db.get_all_alt_sources()
        if all_alt:
            rows = []
            for pn, sources in all_alt.items():
                for s in sources:
                    rows.append({'Part Number': pn, **{k: v for k, v in s.items() if k != 'Part_Number'}})
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("Nessuna fonte alternativa registrata")

    # -------------------------------------------------------------------------
    # SUB-TAB: PROFILI FORNITORE (v4.0)
    # -------------------------------------------------------------------------
    with tab6_sup:
        st.subheader("Profili Fornitore (Tier1→Tier2 Linkage)")
        st.markdown("""
        Registra il profilo specifico di ogni fornitore Tier-1 con informazioni sul fab usato
        e le dipendenze materiali reali (invece dei default categoria+tech_node).

        Il campo **Key Materials Override** (JSON) permette di specificare dipendenze materiali
        personalizzate per questo fornitore. Esempio:
        `{"silicon_wafers": {"dominant_country": "japan", "concentration_risk": 0.60}}`
        """)

        existing_profiles = st.session_state.db.get_all_supplier_profiles()
        if existing_profiles:
            st.dataframe(pd.DataFrame(existing_profiles)[[
                'Supplier_Name', 'Primary_Fab', 'Primary_Fab_Country', 'Wafer_Source'
            ]], use_container_width=True)

        st.markdown("---")
        st.subheader("Aggiungi / Aggiorna Profilo Fornitore")

        with st.form("add_supplier_profile_form"):
            col1, col2 = st.columns(2)
            with col1:
                sp_name = st.text_input("Supplier Name *", placeholder="es. STMicroelectronics")
                sp_fab = st.text_input("Primary Fab", placeholder="es. TSMC Fab 18, Agrate")
                sp_fab_country = st.text_input("Primary Fab Country", placeholder="es. Italy, Taiwan")
            with col2:
                sp_wafer = st.text_input("Wafer Source", placeholder="es. Shin-Etsu (JP)")
                sp_notes = st.text_area("Note", height=60)
            sp_override = st.text_area(
                "Key Materials Override (JSON, opzionale)",
                height=80,
                placeholder='{"silicon_wafers": {"dominant_country": "japan", "concentration_risk": 0.55}}'
            )

            if st.form_submit_button("Salva Profilo Fornitore", type="primary"):
                if not sp_name:
                    st.error("Supplier Name obbligatorio")
                else:
                    d = {
                        'Supplier_Name': sp_name,
                        'Primary_Fab': sp_fab,
                        'Primary_Fab_Country': sp_fab_country,
                        'Wafer_Source': sp_wafer,
                        'Key_Materials_Override': sp_override,
                        'Notes': sp_notes,
                    }
                    if st.session_state.db.add_supplier_profile(d):
                        st.success(f"Profilo fornitore **{sp_name}** salvato!")
                        st.rerun()
                    else:
                        st.error("Errore nel salvataggio")


# =============================================================================
# TAB 7: SIMULATORE WHAT-IF
# =============================================================================

COUNTRY_BLOCK_CONFIG = {
    'Taiwan': {'default_weeks': 8, 'risk_multiplier': 3.0},
    'China': {'default_weeks': 6, 'risk_multiplier': 2.5},
    'Korea': {'default_weeks': 4, 'risk_multiplier': 2.0},
    'Japan': {'default_weeks': 4, 'risk_multiplier': 1.8},
    'Malaysia': {'default_weeks': 3, 'risk_multiplier': 1.5},
    'Singapore': {'default_weeks': 3, 'risk_multiplier': 1.3},
    'Philippines': {'default_weeks': 3, 'risk_multiplier': 1.3},
}

