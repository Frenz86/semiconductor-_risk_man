"""
Modulo per l'esportazione del report in formato PDF
Genera un report PDF professionale con tutti i dati dell'analisi
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO


def generate_pdf_report(batch_results, client_id, run_rate):
    """
    Genera un report PDF completo con tutti i dati dell'analisi.

    Args:
        batch_results: Risultati dell'analisi batch
        client_id: ID del cliente
        run_rate: Run rate utilizzato

    Returns:
        BytesIO: Buffer contenente il PDF generato
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.platypus import KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        st.error("Libreria reportlab non installata. Esegui: pip install reportlab")
        return None

    if not batch_results:
        return None

    components_risk = batch_results.get('components_risk', [])
    bom_risk = batch_results.get('bom_risk', {})
    not_found = batch_results.get('not_found', [])

    # Crea buffer per il PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=1*cm, leftMargin=1*cm,
                           topMargin=1.5*cm, bottomMargin=1*cm)

    # Elementi del documento
    elements = []

    # Stili
    styles = getSampleStyleSheet()

    # Stili personalizzati
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1976D2'),
        alignment=TA_CENTER,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=20
    )

    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1976D2'),
        spaceBefore=10,
        spaceAfter=8
    )

    # ============================================================================
    # HEADER
    # ============================================================================
    elements.append(Paragraph("REPORT RISCHIO SUPPLY CHAIN", title_style))
    elements.append(Paragraph("Analisi deterministica con dipendenze e costi di switching", subtitle_style))

    # Info meta
    report_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    meta_data = [
        ["Cliente:", client_id, "Data:", report_date],
        ["Run Rate:", f"{run_rate:,} PCB/settimana", "Componenti:", f"{len(components_risk)}"]
    ]
    meta_table = Table(meta_data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.grey),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.5*cm))

    # ============================================================================
    # KPI RISCHIO
    # ============================================================================
    elements.append(Paragraph("1. PANORAMICA RISCHIO", header_style))

    high_risk = sum(1 for c in components_risk if c.get('risk_level') == 'ALTO')
    medium_risk = sum(1 for c in components_risk if c.get('risk_level') == 'MEDIO')
    low_risk = sum(1 for c in components_risk if c.get('risk_level') == 'BASSO')
    spof_count = sum(1 for c in components_risk if c.get('is_spof', False))

    kpi_data = [
        ["Rischio Alto", f"{high_risk}", "Rischio Medio", f"{medium_risk}"],
        ["Rischio Basso", f"{low_risk}", "SPOF", f"{spof_count}"],
    ]

    kpi_table = Table(kpi_data, colWidths=[4*cm, 3*cm, 4*cm, 3*cm])
    kpi_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        # Colore rischio alto
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#ffebee')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.HexColor('#d32f2f')),
        # Colore rischio medio
        ('BACKGROUND', (2, 0), (3, 0), colors.HexColor('#fff3e0')),
        ('TEXTCOLOR', (2, 0), (3, 0), colors.HexColor('#f57c00')),
        # Colore rischio basso
        ('BACKGROUND', (0, 1), (1, 1), colors.HexColor('#e8f5e9')),
        ('TEXTCOLOR', (0, 1), (1, 1), colors.HexColor('#388e3c')),
        # Colore SPOF
        ('BACKGROUND', (2, 1), (3, 1), colors.HexColor('#ffebee')),
        ('TEXTCOLOR', (2, 1), (3, 1), colors.HexColor('#d32f2f')),
        ('CELLPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.3*cm))

    # ============================================================================
    # KPI SWITCHING
    # ============================================================================
    elements.append(Paragraph("2. COSTI DI SWITCHING", header_style))

    critical_sw = sum(1 for c in components_risk if c.get('switching_cost', {}).get('classification') == 'CRITICO')
    complex_sw = sum(1 for c in components_risk if c.get('switching_cost', {}).get('classification') == 'COMPLESSO')
    moderate_sw = sum(1 for c in components_risk if c.get('switching_cost', {}).get('classification') == 'MODERATO')
    trivial_sw = sum(1 for c in components_risk if c.get('switching_cost', {}).get('classification') == 'TRIVIALE')

    sw_data = [
        ["Critico", f"{critical_sw}", "Complesso", f"{complex_sw}"],
        ["Moderato", f"{moderate_sw}", "Triviale", f"{trivial_sw}"],
    ]

    sw_table = Table(sw_data, colWidths=[4*cm, 3*cm, 4*cm, 3*cm])
    sw_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#ffebee')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.HexColor('#d32f2f')),
        ('BACKGROUND', (2, 0), (3, 0), colors.HexColor('#fff3e0')),
        ('TEXTCOLOR', (2, 0), (3, 0), colors.HexColor('#f57c00')),
        ('BACKGROUND', (0, 1), (1, 1), colors.HexColor('#fff8e1')),
        ('TEXTCOLOR', (0, 1), (1, 1), colors.HexColor('#f9a825')),
        ('BACKGROUND', (2, 1), (3, 1), colors.HexColor('#e8f5e9')),
        ('TEXTCOLOR', (2, 1), (3, 1), colors.HexColor('#388e3c')),
        ('CELLPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(sw_table)
    elements.append(Spacer(1, 0.3*cm))

    # ============================================================================
    # BOM RISK SUMMARY
    # ============================================================================
    elements.append(Paragraph("3. RISCHIO COMPLESSIVO BOM", header_style))

    overall_score = bom_risk.get('overall_score', 0)
    risk_level = bom_risk.get('risk_level', 'N/A')

    # Colore in base al livello
    if overall_score >= 55:
        risk_color = colors.HexColor('#d32f2f')
        bg_color = colors.HexColor('#ffebee')
    elif overall_score >= 30:
        risk_color = colors.HexColor('#f57c00')
        bg_color = colors.HexColor('#fff3e0')
    else:
        risk_color = colors.HexColor('#388e3c')
        bg_color = colors.HexColor('#e8f5e9')

    bom_summary = [
        ["Punteggio Complessivo:", f"{overall_score:.1f}/100", "Livello:", risk_level],
        ["Componenti con Dipendenze:", f"{bom_risk.get('components_with_dependencies', 0)}", "SPOF:", f"{bom_risk.get('spof_count', 0)}"]
    ]

    bom_table = Table(bom_summary, colWidths=[4*cm, 4*cm, 2.5*cm, 3.5*cm])
    bom_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('TEXTCOLOR', (2, 0), (3, 0), risk_color),
        ('FONTNAME', (2, 0), (3, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('CELLPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(bom_table)
    elements.append(Spacer(1, 0.3*cm))

    # ============================================================================
    # TABELLA COMPONENTI
    # ============================================================================
    elements.append(Paragraph("4. DETTAGLIO COMPONENTI", header_style))

    # Header tabella
    table_data = [["PN", "Fornitore", "Categoria", "Score", "Rischio", "Switching", "SPOF"]]

    for comp in components_risk:
        risk_level = comp.get('risk_level', 'N/A')
        score = comp.get('overall_score', 0)
        sw = comp.get('switching_cost', {})
        sw_class = sw.get('classification', 'N/A')
        is_spof = 'Sì' if comp.get('is_spof', False) else 'No'

        # Colore sfondo in base al rischio
        if risk_level == 'ALTO':
            row_color = colors.HexColor('#ffebee')
            risk_text = 'ALTO'
            risk_text_color = colors.HexColor('#d32f2f')
        elif risk_level == 'MEDIO':
            row_color = colors.HexColor('#fff3e0')
            risk_text = 'MEDIO'
            risk_text_color = colors.HexColor('#f57c00')
        else:
            row_color = colors.HexColor('#e8f5e9')
            risk_text = 'BASSO'
            risk_text_color = colors.HexColor('#388e3c')

        table_data.append([
            comp.get('part_number', 'N/A')[:15],  # Tronca per spazio
            comp.get('supplier', 'N/A')[:15],
            comp.get('category', 'N/A')[:12],
            f"{score:.0f}",
            risk_text,
            sw_class,
            is_spof
        ])

    # Crea tabella
    comp_table = Table(table_data, colWidths=[3.5*cm, 3.5*cm, 3*cm, 1.5*cm, 2*cm, 2.5*cm, 1.5*cm],
                      repeatRows=1)  # Ripete header su ogni pagina

    # Stili tabella
    comp_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('CELLPADDING', (0, 0), (-1, -1), 4),
    ]))

    # Colora le righe in base al rischio
    for i, row in enumerate(table_data[1:], start=1):
        if row[4] == 'ALTO':
            comp_table.setStyle(TableStyle([
                ('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#d32f2f')),
                ('FONTNAME', (4, i), (4, i), 'Helvetica-Bold'),
            ]))
        elif row[4] == 'MEDIO':
            comp_table.setStyle(TableStyle([
                ('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#f57c00')),
            ]))
        else:
            comp_table.setStyle(TableStyle([
                ('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#388e3c')),
            ]))

    elements.append(comp_table)
    elements.append(Spacer(1, 0.3*cm))

    # ============================================================================
    # TABELLA COSTI SWITCHING
    # ============================================================================
    elements.append(PageBreak())
    elements.append(Paragraph("5. DETTAGLIO COSTI DI SWITCHING", header_style))

    sw_table_data = [["Part Number", "OS", "SW (KB)", "Porting (h)", "Qualifica (h)", "Cert.", "Totale (h)"]]

    for comp in components_risk:
        sw = comp.get('switching_cost', {})
        sw_table_data.append([
            comp.get('part_number', 'N/A')[:20],
            sw.get('os_type', 'N/A')[:8],
            f"{sw.get('sw_size_kb', 0):.0f}",
            f"{sw.get('sw_porting_hours', 0):.0f}",
            f"{sw.get('qualification_hours', 0):.0f}",
            f"{sw.get('certification_multiplier', 1.0):.1f}x",
            f"{sw.get('total_switching_hours', 0):.0f}"
        ])

    sw_detail_table = Table(sw_table_data, colWidths=[4*cm, 2*cm, 1.5*cm, 2*cm, 2*cm, 1.5*cm, 2*cm], repeatRows=1)
    sw_detail_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('CELLPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(sw_detail_table)

    # ============================================================================
    # COMPONENTI NON TROVATI
    # ============================================================================
    if not_found:
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("6. COMPONENTI NON TROVATI", header_style))
        elements.append(Paragraph(f"I seguenti part number non sono presenti nel database: {', '.join(not_found)}",
                                 styles['Normal']))

    # ============================================================================
    # FOOTER
    # ============================================================================
    elements.append(Spacer(1, 1*cm))
    footer_text = Paragraph(
        f"Report generato da Supply Chain Resilience Platform v3.0 - {report_date}<br/>"
        "Documento confidenziale - Uso interno solamente",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    )
    elements.append(footer_text)

    # Genera PDF
    doc.build(elements)

    # Posiziona all'inizio del buffer
    buffer.seek(0)
    return buffer


def show_export_button(batch_results, client_id, run_rate, key=None):
    """
    Mostra il pulsante per esportare il report in PDF.

    Args:
        batch_results: Risultati dell'analisi batch
        client_id: ID del cliente
        run_rate: Run rate utilizzato
        key: Chiave univoca per il pulsante (opzionale)
    """
    if not batch_results:
        st.info("Esegui prima un'analisi multipla per esportare il report.")
        return

    # Genera PDF
    pdf_buffer = generate_pdf_report(batch_results, client_id, run_rate)

    if pdf_buffer is None:
        return

    # Crea download button
    pdf_data = pdf_buffer.getvalue()
    filename = f"report_rischio_{client_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

    # Usa key specificata o generane una univoca
    button_key = key or f"pdf_export_{client_id}_{id(pdf_data)}"

    st.download_button(
        label="📄 Scarica Report PDF",
        data=pdf_data,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True,
        type="primary",
        key=button_key
    )
