"""
analisi_multipla.py — Tab: _extract_bom_client_data, _save_bom_client_data, render_tab_analisi_multipla, _run_batch_analysis
"""

from pathlib import Path
from pdf_export import show_export_button
from excel_export import show_excel_export_button
from narrative_engine import generate_risk_narrative
from risk_engine import calculate_component_risk
from typing import List, Any, Dict
import pandas as pd
import plotly.express as px
import streamlit as st


_DATA_DIR = Path(__file__).parent.parent.parent / 'data'

from ._shared import render_geo_detail, _QTY_COL, _BUF_COL

def _extract_bom_client_data(df_uploaded, pn_col):
    """Estrae qty e buffer stock dalla BOM per ogni PN. Restituisce {PN_UPPER: {col: val}}."""
    qty_data = {}
    for _, row in df_uploaded.iterrows():
        raw_pn = str(row.get(pn_col, '')).strip()
        if not raw_pn or raw_pn.lower() in ('nan', 'none', ''):
            continue
        pn = raw_pn.upper()
        entry = {}
        if _QTY_COL in df_uploaded.columns and pd.notna(row.get(_QTY_COL)):
            try:
                entry[_QTY_COL] = int(float(row[_QTY_COL]))
            except (ValueError, TypeError):
                pass
        if _BUF_COL in df_uploaded.columns and pd.notna(row.get(_BUF_COL)):
            try:
                entry[_BUF_COL] = int(float(row[_BUF_COL]))
            except (ValueError, TypeError):
                pass
        if entry:
            qty_data[pn] = entry
    return qty_data


def _save_bom_client_data(qty_data, batch):
    """Salva qty e buffer in Client_Data per i PN trovati nel batch. Restituisce numero salvati."""
    if not qty_data or not st.session_state.get('current_client') or not batch:
        return 0
    saved = 0
    for comp in batch.get('components_data', []):
        pn = str(comp.get('Part Number', '')).strip().upper()
        if pn in qty_data:
            st.session_state.db.add_part_number(
                pn, qty_data[pn],
                client_id=st.session_state.current_client
            )
            saved += 1
    return saved


def render_tab_analisi_multipla():
    """Tab 2: Analisi Multipla Part Numbers"""
    st.header("Multiple Part Numbers Analysis")

    col1, col2 = st.columns(2)

    # File BOM di esempio disponibili
    BOM_EXAMPLES = {
        "02_BOM_Automotive_ADAS_ECU_15": str(_DATA_DIR / "02_BOM_Automotive_ADAS_ECU_15.xlsx"),
        "03_BOM_Industrial_IoT_Gateway_12": str(_DATA_DIR / "03_BOM_Industrial_IoT_Gateway_12.xlsx"),
        "01_BOM_Input_Template_10": str(_DATA_DIR / "01_BOM_Input_Template_10.xlsx"),
    }

    with col1:
        st.subheader("Load Sample BOM")

        selected_bom = st.selectbox(
            "Select BOM",
            options=list(BOM_EXAMPLES.keys()),
            help="Select a sample BOM to analyze"
        )

        if st.button("Load and Analyze BOM", type="primary"):
            bom_file = BOM_EXAMPLES[selected_bom]
            try:
                # Leggi il file Excel
                xl = pd.ExcelFile(bom_file)
                target_sheet = None
                for sheet in xl.sheet_names:
                    if sheet.upper() == 'INPUTS':
                        target_sheet = sheet
                        break
                if target_sheet is None:
                    target_sheet = xl.sheet_names[0]

                df_raw = pd.read_excel(xl, sheet_name=target_sheet, header=None)
                header_row = None
                for i, row in df_raw.iterrows():
                    row_str = ' '.join(str(v).lower() for v in row.values if pd.notna(v))
                    if 'supplier' in row_str and ('part' in row_str or 'name' in row_str):
                        header_row = i
                        break
                if header_row is not None:
                    df_uploaded = pd.read_excel(xl, sheet_name=target_sheet, header=header_row)
                    df_uploaded = df_uploaded.dropna(how='all')
                else:
                    df_uploaded = pd.read_excel(xl, sheet_name=target_sheet)

                # Trova colonna Part Number
                pn_col = None
                for col in df_uploaded.columns:
                    col_lower = str(col).lower()
                    if 'part' in col_lower and 'number' in col_lower:
                        pn_col = col
                        break
                    if col_lower in ('mpn', 'pn', 'part_number', 'partnumber'):
                        pn_col = col
                        break

                if pn_col:
                    pns = df_uploaded[pn_col].dropna().astype(str).tolist()
                    pns = [p for p in pns if p.strip() and p.strip().lower() not in ('nan', 'none', '')]

                    # Estrai run rate dalla BOM (righe prima dell'header)
                    if header_row is not None and header_row > 0:
                        for i in range(header_row):
                            pre_vals = [str(v) for v in df_raw.iloc[i].values
                                        if pd.notna(v) and str(v) != 'nan']
                            if any('run rate' in v.lower() for v in pre_vals):
                                for v in pre_vals:
                                    try:
                                        rr = int(float(v))
                                        if rr > 0:
                                            st.session_state.run_rate = rr
                                            break
                                    except (ValueError, TypeError):
                                        pass
                                break

                    qty_data = _extract_bom_client_data(df_uploaded, pn_col)
                    st.success(f"Loaded **{len(pns)}** part numbers from **{selected_bom}**")

                    batch = _run_batch_analysis(pns, st.session_state.current_client, st.session_state.run_rate)
                    st.session_state.batch_results = batch

                    saved = _save_bom_client_data(qty_data, batch)
                    if saved > 0:
                        st.caption(f"BOM quantities saved in Client_Data for {saved} components")

                    if st.session_state.get('current_client') and batch:
                        _cid = st.session_state.current_client
                        st.session_state.db.save_analysis_snapshot(
                            client_id=_cid,
                            batch_results=batch,
                            bom_name=selected_bom,
                        )
                        _high = sum(1 for r in batch.get('components_risk', []) if r.get('risk_level') == 'HIGH')
                        st.session_state.db.log_action(
                            client_id=_cid,
                            action_type='risk_analysis',
                            new_value=f"BOM={selected_bom}, HIGH={_high}",
                            notes=f"Batch {len(batch.get('components_risk', []))} componenti",
                        )
                else:
                    st.error("Column 'Part Number' not found in the file.")
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")

    with col2:
        st.subheader("Upload Your File")
        uploaded_file = st.file_uploader(
            "Upload file with Part Numbers list",
            type=['csv', 'xlsx', 'xls'],
            help="The file must have a 'Part Number' column"
        )

        if uploaded_file:
            try:
                df_raw = None
                header_row = None
                if uploaded_file.name.endswith('.csv'):
                    df_uploaded = pd.read_csv(uploaded_file)
                else:
                    xl = pd.ExcelFile(uploaded_file)
                    target_sheet = None
                    for sheet in xl.sheet_names:
                        if sheet.upper() == 'INPUTS':
                            target_sheet = sheet
                            break
                    if target_sheet is None:
                        target_sheet = xl.sheet_names[0]

                    df_raw = pd.read_excel(xl, sheet_name=target_sheet, header=None)
                    for i, row in df_raw.iterrows():
                        row_str = ' '.join(str(v).lower() for v in row.values if pd.notna(v))
                        if 'supplier' in row_str and ('part' in row_str or 'name' in row_str):
                            header_row = i
                            break
                    if header_row is not None:
                        df_uploaded = pd.read_excel(xl, sheet_name=target_sheet, header=header_row)
                        df_uploaded = df_uploaded.dropna(how='all')
                    else:
                        df_uploaded = pd.read_excel(xl, sheet_name=target_sheet)

                pn_col = None
                for col in df_uploaded.columns:
                    col_lower = str(col).lower()
                    if 'part' in col_lower and 'number' in col_lower:
                        pn_col = col
                        break
                    if col_lower in ('mpn', 'pn', 'part_number', 'partnumber'):
                        pn_col = col
                        break

                if pn_col:
                    pns = df_uploaded[pn_col].dropna().astype(str).tolist()
                    pns = [p for p in pns if p.strip() and p.strip().lower() not in ('nan', 'none', '')]

                    # Estrai run rate dalla BOM (solo Excel, righe prima dell'header)
                    if df_raw is not None and header_row is not None and header_row > 0:
                        for i in range(header_row):
                            pre_vals = [str(v) for v in df_raw.iloc[i].values
                                        if pd.notna(v) and str(v) != 'nan']
                            if any('run rate' in v.lower() for v in pre_vals):
                                for v in pre_vals:
                                    try:
                                        rr = int(float(v))
                                        if rr > 0:
                                            st.session_state.run_rate = rr
                                            break
                                    except (ValueError, TypeError):
                                        pass
                                break

                    qty_data = _extract_bom_client_data(df_uploaded, pn_col)
                    st.success(f"Found **{len(pns)}** part numbers in the file")

                    if st.button("Analyze Uploaded File", type="primary"):
                        batch = _run_batch_analysis(pns, st.session_state.current_client, st.session_state.run_rate)
                        st.session_state.batch_results = batch

                        saved = _save_bom_client_data(qty_data, batch)
                        if saved > 0:
                            st.caption(f"BOM quantities saved in Client_Data for {saved} components")

                        if st.session_state.get('current_client') and batch:
                            _cid = st.session_state.current_client
                            st.session_state.db.save_analysis_snapshot(
                                client_id=_cid,
                                batch_results=batch,
                                bom_name=uploaded_file.name,
                            )
                            _high = sum(1 for r in batch.get('components_risk', []) if r.get('risk_level') == 'HIGH')
                            st.session_state.db.log_action(
                                client_id=_cid,
                                action_type='risk_analysis',
                                new_value=f"BOM={uploaded_file.name}, HIGH={_high}",
                                notes=f"Batch upload {len(batch.get('components_risk', []))} componenti",
                            )
                else:
                    st.error("Column 'Part Number' not found in the file. Columns found: " +
                             ", ".join(str(c) for c in df_uploaded.columns[:10]))
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")

    # Mostra risultati batch
    batch = st.session_state.batch_results
    if batch:
        st.markdown("---")

        # Pulsanti export
        st.subheader("📄 Export Report")
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            show_export_button(batch, st.session_state.current_client, st.session_state.run_rate, key="export_tab_multipla")
        with col_exp2:
            show_excel_export_button(batch, st.session_state.current_client, st.session_state.run_rate, key="excel_tab_multipla")
        st.markdown("---")

        st.success(f"Found **{batch['found_count']}** of **{batch['total_count']}** part numbers")

        # Dashboard metriche
        col1, col2, col3, col4, col5 = st.columns(5)

        risks = batch['components_risk']

        with col1:
            red_count = sum(1 for r in risks if r['color'] == 'RED')
            st.metric("High Risk", red_count)

        with col2:
            yellow_count = sum(1 for r in risks if r['color'] == 'YELLOW')
            st.metric("Medium Risk", yellow_count)

        with col3:
            green_count = sum(1 for r in risks if r['color'] == 'GREEN')
            st.metric("Low Risk", green_count)

        with col4:
            total_mh = sum(r['man_hours'] for r in risks)
            st.metric("Total Man-Hours", f"{total_mh:,}h")

        with col5:
            spof_count = len(batch['bom_risk'].get('spofs', []))
            st.metric("Single Points of Failure", spof_count)

        # Grafici
        col1, col2 = st.columns(2)

        with col1:
            risk_counts = {
                'High (RED)': red_count,
                'Medium (YELLOW)': yellow_count,
                'Low (GREEN)': green_count
            }
            fig_pie = px.pie(
                values=list(risk_counts.values()),
                names=list(risk_counts.keys()),
                color=list(risk_counts.keys()),
                color_discrete_map={
                    'High (RED)': '#ff4444',
                    'Medium (YELLOW)': '#ffbb33',
                    'Low (GREEN)': '#00C851'
                },
                title="Distribution by Risk Level"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            sw_counts = {'TRIVIALE': 0, 'MODERATO': 0, 'COMPLESSO': 0, 'CRITICO': 0}
            for r in risks:
                cls = r.get('switching_cost', {}).get('classification', 'TRIVIALE')
                sw_counts[cls] = sw_counts.get(cls, 0) + 1

            fig_sw = px.pie(
                values=list(sw_counts.values()),
                names=list(sw_counts.keys()),
                color=list(sw_counts.keys()),
                color_discrete_map={
                    'TRIVIALE': '#00C851',
                    'MODERATO': '#ffbb33',
                    'COMPLESSO': '#ff8800',
                    'CRITICO': '#ff4444'
                },
                title="Switching Cost Distribution"
            )
            st.plotly_chart(fig_sw, use_container_width=True)

        # Dettaglio rischi per componente
        st.subheader("Risk Detail by Component")

        for risk in sorted(risks, key=lambda x: x['score'], reverse=True):
            color_emoji = "🔴" if risk['color'] == 'RED' else "🟡" if risk['color'] == 'YELLOW' else "🟢"
            sw = risk.get('switching_cost', {})
            sw_class = sw.get('classification', 'N/A')

            with st.expander(
                f"{color_emoji} **{risk['part_number']}** | {risk['supplier']} | Score: {risk['score']} | Switching: {sw_class}",
                expanded=(risk['color'] == 'RED')
            ):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Risk Factors:**")
                    if risk['factors']:
                        for factor in risk['factors']:
                            st.markdown(f"- {factor}")
                    else:
                        st.markdown("- No significant factors")

                with col2:
                    st.markdown("**Suggestions:**")
                    if risk['suggestions']:
                        for suggestion in risk['suggestions']:
                            st.markdown(f"- {suggestion}")
                    else:
                        st.markdown("- No action required")

                with col3:
                    st.markdown("**Geo Risk Frontend/Backend:**")
                    geo = risk.get('geo_risk', {})
                    render_geo_detail(geo)
                    st.markdown(f"**Man-Hours:** {risk['man_hours']}h")
                    st.markdown(f"**Switching:** {sw.get('total_switching_hours', 0):.0f}h ({sw_class})")

                if risk['color'] == 'RED':
                    st.markdown("---")
                    st.markdown("**AI Risk Summary:**")
                    st.info(generate_risk_narrative(risk))

                    # Risk Ownership (GRC v4.3)
                    client_id = st.session_state.get('current_client', '')
                    pn = risk['part_number']
                    owner_data = st.session_state.db.get_risk_owner(client_id, pn) if client_id else {'owner': '', 'status': 'Open'}
                    col_own1, col_own2, col_own3 = st.columns([2, 1.5, 1])
                    with col_own1:
                        new_owner = st.text_input("Risk Owner", value=owner_data['owner'],
                                                   key=f"owner_{pn}", placeholder="Name / Team")
                    with col_own2:
                        new_status = st.selectbox("Status", ['Open', 'In Progress', 'Accepted', 'Mitigated'],
                                                   index=['Open', 'In Progress', 'Accepted', 'Mitigated'].index(owner_data['status']) if owner_data['status'] in ['Open', 'In Progress', 'Accepted', 'Mitigated'] else 0,
                                                   key=f"status_{pn}")
                    with col_own3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Save", key=f"save_owner_{pn}"):
                            if client_id:
                                old_owner_data = st.session_state.db.get_risk_owner(client_id, pn)
                                st.session_state.db.update_risk_owner(client_id, pn, new_owner, new_status)
                                st.session_state.db.log_action(
                                    client_id=client_id,
                                    action_type='owner_assigned',
                                    target_pn=pn,
                                    old_value=f"owner={old_owner_data.get('owner','')}, status={old_owner_data.get('status','')}",
                                    new_value=f"owner={new_owner}, status={new_status}",
                                )
                                st.success("Saved")

        # PN non trovati
        if batch['not_found']:
            st.warning(f"**{len(batch['not_found'])}** part numbers not found: {', '.join(batch['not_found'])}")


# =============================================================================
# TAB 3: ALBERO DIPENDENZE
# =============================================================================


def _run_batch_analysis(pns: List[str], client_id, run_rate):
    """Esegue analisi batch e restituisce risultati strutturati. v4.0: include EMS, distributori, alt sources."""
    from risk_engine import calculate_bom_risk_v3

    results = st.session_state.db.lookup_batch(pns, client_id)
    found_components = {pn: data for pn, data in results.items() if data is not None}
    not_found = [pn for pn, data in results.items() if data is None]

    if not found_components:
        return None

    # v4.0 - Carica dati filiera commerciale dal DB
    db = st.session_state.db

    # EMS providers indicizzati per nome (uppercase)
    ems_all = db.get_all_ems_providers()
    ems_by_name = {str(e.get('EMS_Name', '')).upper(): e for e in ems_all}

    # Distributori associati per PN
    all_part_distributors = db.get_all_part_distributors()

    # Fonti alternative per PN
    all_alt_sources = db.get_all_alt_sources()

    # Profili fornitore per nome (uppercase)
    supplier_profiles_all = db.get_all_supplier_profiles()
    supplier_profiles_by_name = {str(s.get('Supplier_Name', '')).upper(): s for s in supplier_profiles_all}

    # v4.1 - Dipendenze IP per PN
    all_ip_dependencies = db.get_all_ip_dependencies()

    # Calcola rischi individuali
    components_data = []
    components_risk = []
    for pn, data in found_components.items():
        pn_upper = pn.upper()

        # Recupera dati filiera per questo PN
        ems_name = str(data.get('EMS_Name', '') or '').upper()
        ems_profile = ems_by_name.get(ems_name) if ems_name else None

        dist_list = all_part_distributors.get(pn_upper, [])
        alt_sources = all_alt_sources.get(pn_upper, [])
        ip_deps = all_ip_dependencies.get(pn_upper, [])

        supplier_name = str(data.get('Supplier Name', '') or '').upper()
        supplier_profile = supplier_profiles_by_name.get(supplier_name)

        risk = calculate_component_risk(
            data, run_rate,
            ems_provider_data=ems_profile,
            distributor_list=dist_list,
            alt_sources=alt_sources,
            ip_dependencies=ip_deps,
        )
        risk['part_number'] = pn
        risk['supplier'] = data.get('Supplier Name', 'N/A')
        risk['category'] = data.get('Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)', 'N/A')
        risk['supplier_profile'] = supplier_profile  # Per tier2 con profilo fornitore
        components_risk.append(risk)
        data['Part Number'] = pn
        components_data.append(data)  # FIX: spostato fuori dal blocco risk appetite

    # v4.3 - Applica risk appetite del cliente (soglie personalizzate)
    if client_id:
        appetite = st.session_state.db.get_client_risk_appetite(client_id)
        for risk in components_risk:
            score = risk['score']
            if score >= appetite['high']:
                risk['color'] = 'RED'
                risk['risk_level'] = 'HIGH'
            elif score >= appetite['medium']:
                risk['color'] = 'YELLOW'
                risk['risk_level'] = 'MEDIUM'
            else:
                risk['color'] = 'GREEN'
                risk['risk_level'] = 'LOW'

    # Calcola BOM risk v3 (con dependency graph)
    bom_risk_v3 = calculate_bom_risk_v3(components_data, components_risk)

    return {
        'components_data': components_data,
        'components_risk': components_risk,
        'bom_risk': bom_risk_v3,
        'found_count': len(found_components),
        'total_count': len(pns),
        'not_found': not_found,
    }

