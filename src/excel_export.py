"""
excel_export.py — Export report multi-foglio in formato Excel (.xlsx)
v4.2: Foglio 1 Summary KPI, Foglio 2 Dettaglio Componenti, Foglio 3 Switching Costs, Foglio 4 Tier-2 Bottlenecks
"""

from io import BytesIO
from datetime import datetime
import pandas as pd


def generate_excel_report(batch_results: dict, client_id: str, run_rate: int = 0) -> BytesIO | None:
    """
    Genera un report Excel multi-foglio dal risultato di un'analisi batch.

    Args:
        batch_results: Risultato di _run_batch_analysis() con chiavi:
                       components_risk, bom_risk, not_found, components_data
        client_id: ID del cliente
        run_rate: PCB/settimana (per metadati)

    Returns:
        BytesIO contenente il file .xlsx, o None se batch_results è vuoto
    """
    if not batch_results:
        return None

    try:
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from openpyxl import load_workbook
    except ImportError:
        return None

    components_risk = batch_results.get('components_risk', [])
    bom_risk = batch_results.get('bom_risk', {})
    not_found = batch_results.get('not_found', [])

    if not components_risk:
        return None

    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:

        # =====================================================================
        # FOGLIO 1 — Summary KPI
        # =====================================================================
        high = sum(1 for r in components_risk if r.get('color') == 'RED')
        med = sum(1 for r in components_risk if r.get('color') == 'YELLOW')
        low = sum(1 for r in components_risk if r.get('color') == 'GREEN')
        spof = len(bom_risk.get('spofs', []))
        avg_score = sum(r.get('score', 0) for r in components_risk) / len(components_risk) if components_risk else 0
        total_mh = sum(r.get('man_hours', 0) for r in components_risk)

        summary_data = {
            'Metric': [
                'Client', 'Date', 'Run Rate (PCB/week)',
                'Total Components', 'Avg Risk Score', 'BOM Risk Level',
                'High Risk (RED)', 'Medium Risk (YELLOW)', 'Low Risk (GREEN)',
                'SPOF Count', 'Total Man-Hours', 'BOM Value ($)',
                'Not Found in DB',
            ],
            'Value': [
                client_id,
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                run_rate,
                len(components_risk),
                f"{avg_score:.1f}/100",
                bom_risk.get('risk_level', 'N/A'),
                high,
                med,
                low,
                spof,
                f"{total_mh:.0f}h",
                f"${bom_risk.get('total_bom_value', 0):,.0f}",
                len(not_found),
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary KPI', index=False)

        # =====================================================================
        # FOGLIO 2 — Dettaglio Componenti
        # =====================================================================
        rows_detail = []
        for r in sorted(components_risk, key=lambda x: x.get('score', 0), reverse=True):
            sw = r.get('switching_cost', {})
            geo = r.get('geo_risk', {})
            rows_detail.append({
                'Part Number': r.get('part_number', ''),
                'Supplier': r.get('supplier', ''),
                'Category': r.get('category', ''),
                'Risk Score': round(r.get('score', 0), 1),
                'Risk Level': r.get('risk_level', ''),
                'Color': r.get('color', ''),
                'SPOF': 'Yes' if r.get('is_spof') else 'No',
                'Frontend Country': r.get('frontend_country', ''),
                'Backend Country': r.get('backend_country', ''),
                'Technology Node': r.get('technology_node', ''),
                'Lead Time (weeks)': r.get('lead_time', ''),
                'Buffer Coverage (weeks)': round(r.get('buffer_coverage_weeks', 0), 1),
                'EOL Status': r.get('eol_status', ''),
                'Allocation Status': r.get('allocation_status', ''),
                'Alt Sources': r.get('alternative_sources_count', 0),
                'Hidden SPOF Score': r.get('hidden_spof', {}).get('hidden_spof_score', 0),
                'EMS Score': r.get('ems_detail', {}).get('ems_score', 0),
                'Distributor Score': r.get('distributor_detail', {}).get('distributor_score', 0),
                'IP Score': r.get('ip_risk', {}).get('ip_score', 0),
                'Switching Class': sw.get('classification', ''),
                'Switching Hours': sw.get('total_switching_hours', 0),
                'Man-Hours Mitigation': r.get('man_hours', 0),
                'Unit Price ($)': r.get('unit_price', 0),
                'Suggestions': '; '.join(r.get('suggestions', [])),
            })
        df_detail = pd.DataFrame(rows_detail)
        df_detail.to_excel(writer, sheet_name='Component Detail', index=False)

        # =====================================================================
        # FOGLIO 3 — Switching Costs
        # =====================================================================
        rows_sw = []
        for r in components_risk:
            sw = r.get('switching_cost', {})
            rows_sw.append({
                'Part Number': r.get('part_number', ''),
                'Supplier': r.get('supplier', ''),
                'Category': r.get('category', ''),
                'OS Type': sw.get('os_type', ''),
                'SW Size (KB)': sw.get('sw_size_kb', 0),
                'SW Porting Hours': round(sw.get('sw_porting_hours', 0), 1),
                'Qualification Weeks': sw.get('qualification_weeks', 0),
                'Qualification Hours': round(sw.get('qualification_hours', 0), 1),
                'Certification': r.get('certification', ''),
                'Cert Multiplier': sw.get('certification_multiplier', 1.0),
                'Total Switching Hours': round(sw.get('total_switching_hours', 0), 1),
                'Classification': sw.get('classification', ''),
            })
        df_sw = pd.DataFrame(rows_sw)
        df_sw.to_excel(writer, sheet_name='Switching Costs', index=False)

        # =====================================================================
        # FOGLIO 4 — Tier-2 Bottlenecks
        # =====================================================================
        rows_t2 = []
        for r in components_risk:
            t2 = r.get('tier2_risk', {})
            materials = t2.get('critical_materials', [])
            if materials:
                for mat in materials:
                    rows_t2.append({
                        'Part Number': r.get('part_number', ''),
                        'Supplier': r.get('supplier', ''),
                        'Material': mat.get('material_name', mat.get('material_key', '')),
                        'Dominant Country': mat.get('dominant_country', ''),
                        'Concentration (%)': mat.get('concentration_pct', 0),
                        'Criticality': mat.get('criticality', ''),
                        'Substitutability': mat.get('substitutability', ''),
                        'Tier-2 Score': round(t2.get('tier2_score', 0), 1),
                    })
            else:
                rows_t2.append({
                    'Part Number': r.get('part_number', ''),
                    'Supplier': r.get('supplier', ''),
                    'Material': '',
                    'Dominant Country': '',
                    'Concentration (%)': 0,
                    'Criticality': '',
                    'Substitutability': '',
                    'Tier-2 Score': round(t2.get('tier2_score', 0), 1),
                })
        if rows_t2:
            df_t2 = pd.DataFrame(rows_t2)
        else:
            df_t2 = pd.DataFrame(columns=['Part Number', 'Supplier', 'Material',
                                           'Dominant Country', 'Concentration (%)',
                                           'Criticality', 'Substitutability', 'Tier-2 Score'])
        df_t2.to_excel(writer, sheet_name='Tier-2 Bottlenecks', index=False)

    # Applica stili (colori header + colori righe rischio) tramite openpyxl
    buffer.seek(0)
    wb = load_workbook(buffer)
    _apply_excel_styles(wb, components_risk)

    styled_buffer = BytesIO()
    wb.save(styled_buffer)
    styled_buffer.seek(0)
    return styled_buffer


def _apply_excel_styles(wb, components_risk):
    """Applica stili: header blu + colore righe in Component Detail per livello rischio."""
    try:
        from openpyxl.styles import PatternFill, Font, Alignment
        from openpyxl.utils import get_column_letter

        HEADER_FILL = PatternFill(start_color='1976D2', end_color='1976D2', fill_type='solid')
        HEADER_FONT = Font(color='FFFFFF', bold=True)
        RED_FILL = PatternFill(start_color='FFEBEE', end_color='FFEBEE', fill_type='solid')
        YELLOW_FILL = PatternFill(start_color='FFF3E0', end_color='FFF3E0', fill_type='solid')
        GREEN_FILL = PatternFill(start_color='E8F5E9', end_color='E8F5E9', fill_type='solid')

        # Mappa part number -> colore
        color_map = {r.get('part_number', ''): r.get('color', '') for r in components_risk}

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            # Header row styling
            for cell in ws[1]:
                cell.fill = HEADER_FILL
                cell.font = HEADER_FONT
                cell.alignment = Alignment(horizontal='center', vertical='center')

            # Autofit larghezza colonne (approssimato)
            for col_idx, col in enumerate(ws.columns, 1):
                max_len = max((len(str(cell.value or '')) for cell in col), default=10)
                ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 40)

            # Colora righe in Component Detail
            if sheet_name == 'Component Detail':
                for row in ws.iter_rows(min_row=2):
                    pn_cell = row[0].value
                    color = color_map.get(str(pn_cell), '')
                    fill = RED_FILL if color == 'RED' else YELLOW_FILL if color == 'YELLOW' else GREEN_FILL
                    for cell in row:
                        cell.fill = fill
    except Exception:
        pass


def show_excel_export_button(batch_results: dict, client_id: str, run_rate: int = 0, key: str = 'excel_export'):
    """
    Mostra il bottone per scaricare il report Excel.

    Args:
        batch_results: Risultati batch
        client_id: ID del cliente
        run_rate: Run rate
        key: Chiave Streamlit univoca
    """
    import streamlit as st

    if not batch_results:
        return

    excel_buffer = generate_excel_report(batch_results, client_id, run_rate)
    if excel_buffer is None:
        st.warning("openpyxl not installed. Run: pip install openpyxl")
        return

    filename = f"report_{client_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    st.download_button(
        label="📊 Download Excel Report",
        data=excel_buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="secondary",
        key=key,
    )
