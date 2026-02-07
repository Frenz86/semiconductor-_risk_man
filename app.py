"""
Supply Chain Risk Assessment Tool
=================================
App Streamlit per valutare il rischio della supply chain elettronica.

Per eseguire:
1. pip install streamlit pandas openpyxl xlsxwriter plotly
2. streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from io import BytesIO
from pathlib import Path

# Configurazione pagina
st.set_page_config(
                    page_title="Supply Chain Risk Assessment",
                    page_icon="🔌",
                    layout="wide"
                )

# CSS personalizzato
st.markdown("""
<style>
    .risk-red { background-color: #ff4444; color: white; padding: 10px; border-radius: 5px; text-align: center; }
    .risk-yellow { background-color: #ffbb33; color: black; padding: 10px; border-radius: 5px; text-align: center; }
    .risk-green { background-color: #00C851; color: white; padding: 10px; border-radius: 5px; text-align: center; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin: 10px 0; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# MOTORE DI CALCOLO DEL RISCHIO
# =============================================================================

def calculate_component_risk(row, run_rate):
    """Calcola il rischio per un singolo componente"""
    
    score = 0
    factors = []
    suggestions = []
    man_hours = 0
    
    # Estrai i paesi degli stabilimenti
    countries = []
    for col in ['Country of Manufacturing Plant 1', 'Country of Manufacturing Plant 2', 
                'Country of Manufacturing Plant 3', 'Country of Manufacturing Plant 4']:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            countries.append(str(row[col]).strip())
    
    high_risk_countries = ['taiwan', 'china', 'korea', 'japan', 'malaysia', 'singapore', 'philippines']
    
    # 1. RISCHIO CONCENTRAZIONE GEOGRAFICA (25%)
    if countries:
        unique_countries = list(set(countries))
        asia_count = sum(1 for c in countries if any(hr in c.lower() for hr in high_risk_countries))
        
        if len(unique_countries) == 1 and asia_count > 0:
            score += 25
            factors.append(f"🌏 CRITICO: Tutti gli stabilimenti in {unique_countries[0]}")
            suggestions.append("Diversificare con fornitori in EU/Americas")
            man_hours += 40
        elif asia_count == len(countries) and len(countries) > 0:
            score += 20
            factors.append("🌏 ALTO: Tutti gli stabilimenti in area Asia-Pacifico")
            suggestions.append("Considerare fornitori con stabilimenti in EU/Americas")
            man_hours += 30
        elif asia_count > len(countries) / 2:
            score += 12
            factors.append("🌏 MEDIO: Maggioranza stabilimenti in Asia")
    
    # 2. RISCHIO SINGLE SOURCE (20%)
    num_plants = len(countries)
    if num_plants == 1:
        score += 20
        factors.append("🏭 CRITICO: Un solo stabilimento produttivo")
        suggestions.append("Identificare e qualificare second source")
        weeks_qual = row.get('Weeks to qualify', 12)
        if pd.notna(weeks_qual):
            man_hours += int(weeks_qual) * 40
        else:
            man_hours += 200
    elif num_plants == 2:
        score += 10
        factors.append("🏭 MEDIO: Solo 2 stabilimenti produttivi")
    
    # 3. RISCHIO LEAD TIME (15%)
    lead_time = row.get('Supplier Lead Time (weeks)', 0)
    if pd.notna(lead_time):
        lead_time = int(lead_time)
        if lead_time > 16:
            score += 15
            factors.append(f"⏱️ CRITICO: Lead time molto lungo ({lead_time} settimane)")
            suggestions.append("Negoziare rolling forecast o VMI con il fornitore")
            man_hours += 16
        elif lead_time > 10:
            score += 10
            factors.append(f"⏱️ ALTO: Lead time lungo ({lead_time} settimane)")
            suggestions.append("Implementare rolling forecast")
            man_hours += 8
        elif lead_time > 6:
            score += 5
            factors.append(f"⏱️ MEDIO: Lead time moderato ({lead_time} settimane)")
    
    # 4. RISCHIO BUFFER STOCK (15%)
    buffer_stock = row.get('If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units', 0)
    qty_per_bom = row.get('How Many Device of this specific PN are in the BOM?', 1)
    
    if pd.notna(buffer_stock) and pd.notna(qty_per_bom) and pd.notna(lead_time):
        try:
            buffer_stock = float(buffer_stock)
            qty_per_bom = float(qty_per_bom) if float(qty_per_bom) > 0 else 1
            weekly_consumption = run_rate * qty_per_bom
            
            if weekly_consumption > 0:
                coverage_weeks = buffer_stock / weekly_consumption
                
                if coverage_weeks < lead_time:
                    score += 15
                    factors.append(f"📦 CRITICO: Buffer copre solo {coverage_weeks:.1f} settimane (lead time: {lead_time})")
                    suggestions.append(f"Aumentare buffer stock ad almeno {lead_time * 1.5:.0f} settimane di copertura")
                    man_hours += 8
                elif coverage_weeks < lead_time * 1.5:
                    score += 8
                    factors.append(f"📦 MEDIO: Buffer copre {coverage_weeks:.1f} settimane")
        except:
            pass
    
    # 5. RISCHIO DIPENDENZE (10%)
    standalone = row.get('Stand-Alone Functional Device (Y/N)', 'Y')
    if pd.notna(standalone) and str(standalone).upper() == 'N':
        score += 10
        dependency = row.get('In case answer on Column C is Y, Which other device in the BOM is necessary to run the PN on Column B? (e.g. PMIC for MPU, Memory for MPU)', '')
        if pd.notna(dependency) and dependency:
            factors.append(f"🔗 ALTO: Dipende da altri componenti ({dependency})")
        else:
            factors.append("🔗 ALTO: Dipende da altri componenti nella BOM")
        suggestions.append("Verificare allineamento rischio con componenti dipendenti")
    
    # 6. RISCHIO PROPRIETARY (10%)
    proprietary = row.get('Proprietary (Y/N)**', 'N')
    commodity = row.get('Commodity (Y/N)*', 'Y')
    
    if pd.notna(proprietary) and str(proprietary).upper() == 'Y':
        score += 10
        factors.append("🔒 ALTO: Componente proprietario (no alternative dirette)")
        suggestions.append("Avviare studio di redesign con componente commodity/standard")
        man_hours += 200
    elif pd.notna(commodity) and str(commodity).upper() == 'N':
        score += 5
        factors.append("🔒 MEDIO: Componente non-commodity")
    
    # 7. RISCHIO CERTIFICAZIONI (5%)
    weeks_qualify = row.get('Weeks to qualify', 0)
    certification = row.get('Specify Certification/Qualification', '')
    
    if pd.notna(weeks_qualify) and int(weeks_qualify) > 12:
        score += 5
        factors.append(f"📋 MEDIO: Riqualifica lunga ({int(weeks_qualify)} settimane)")
        if pd.notna(certification) and certification:
            factors[-1] += f" - {certification}"
        suggestions.append("Pre-qualificare alternative prima di potenziale EOL")
        man_hours += 16
    
    # Determina colore rischio
    if score >= 55:
        color = "RED"
        risk_level = "ALTO"
    elif score >= 30:
        color = "YELLOW"
        risk_level = "MEDIO"
    else:
        color = "GREEN"
        risk_level = "BASSO"
    
    return {
        'score': score,
        'color': color,
        'risk_level': risk_level,
        'factors': factors,
        'suggestions': suggestions,
        'man_hours': man_hours
    }


def calculate_bom_risk(components_risk, df):
    """Calcola il rischio complessivo della BOM pesato per valore"""
    
    if not components_risk:
        return {'score': 0, 'color': 'GREEN', 'risk_level': 'N/A'}
    
    total_value = 0
    weighted_score = 0
    
    for i, risk in enumerate(components_risk):
        if i < len(df):
            price = df.iloc[i].get('Unit Price ($)', 1)
            qty = df.iloc[i].get('How Many Device of this specific PN are in the BOM?', 1)
            
            price = float(price) if pd.notna(price) else 1
            qty = float(qty) if pd.notna(qty) else 1
            
            value = price * qty
            total_value += value
            weighted_score += risk['score'] * value
    
    if total_value > 0:
        avg_score = weighted_score / total_value
    else:
        avg_score = sum(r['score'] for r in components_risk) / len(components_risk)
    
    if avg_score >= 50:
        return {'score': avg_score, 'color': 'RED', 'risk_level': 'ALTO'}
    elif avg_score >= 30:
        return {'score': avg_score, 'color': 'YELLOW', 'risk_level': 'MEDIO'}
    else:
        return {'score': avg_score, 'color': 'GREEN', 'risk_level': 'BASSO'}


# =============================================================================
# INTERFACCIA UTENTE
# =============================================================================

st.title("🔌 Supply Chain Risk Assessment Tool")
st.markdown("**Valutazione del rischio della supply chain per componenti elettronici**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Parametri")
    run_rate = st.number_input("Run Rate (PCB/settimana)", min_value=1, value=5000, step=100)

    st.markdown("---")
    st.header("📊 Legenda Rischio")
    st.markdown('<div class="risk-red">🔴 ALTO (≥55 punti)</div>', unsafe_allow_html=True)
    st.markdown('<div class="risk-yellow">🟡 MEDIO (30-54 punti)</div>', unsafe_allow_html=True)
    st.markdown('<div class="risk-green">🟢 BASSO (<30 punti)</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.header("ℹ️ Info")
    st.markdown("""
    **Fattori di rischio:**
    - Concentrazione geografica (25%)
    - Single source (20%)
    - Lead time (15%)
    - Buffer stock (15%)
    - Dipendenze (10%)
    - Proprietario/Commodity (10%)
    - Certificazioni (5%)
    """)

# Tabs
tab1, tab2, tab3 = st.tabs(["📁 Analisi BOM", "📊 Grafo Algoritmo Utilizzato", "ℹ️ Guida"])

with tab1:
    st.header("📁 Carica File BOM")
    uploaded_file = st.file_uploader(
        "Trascina qui il file Excel con i dati dei componenti",
        type=['xlsx', 'xls'],
        help="Il file deve contenere un foglio 'INPUTS' con i dati dei componenti"
    )

    if uploaded_file is not None:
        try:
            # Leggi il file
            xl = pd.ExcelFile(uploaded_file)

            # Cerca il foglio INPUTS
            if 'INPUTS' in xl.sheet_names:
                df_raw = pd.read_excel(uploaded_file, sheet_name='INPUTS', header=None)

                # Trova la riga header (quella con "Supplier Name")
                header_row = None
                for i, row in df_raw.iterrows():
                    if 'Supplier Name' in row.values:
                        header_row = i
                        break

                if header_row is not None:
                    # Rileggi con l'header corretto
                    df = pd.read_excel(uploaded_file, sheet_name='INPUTS', header=header_row)
                    # Rimuovi righe vuote
                    df = df.dropna(subset=['Supplier Name'])

                    st.success(f"✅ File caricato! Trovati **{len(df)} componenti**")

                    # Mostra dati caricati
                    with st.expander("📋 Visualizza dati caricati", expanded=False):
                        st.dataframe(df, use_container_width=True)

                    # Calcola rischi
                    st.header("📊 Risultati Analisi Rischio")

                    components_risk = []
                    for idx, row in df.iterrows():
                        risk = calculate_component_risk(row, run_rate)
                        risk['supplier'] = row.get('Supplier Name', 'N/A')
                        risk['part_number'] = row.get('Supplier Part Number', 'N/A')
                        risk['category'] = row.get('Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)', 'N/A')
                        components_risk.append(risk)

                    # Rischio BOM complessivo
                    bom_risk = calculate_bom_risk(components_risk, df)

                    # Dashboard metriche
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        color_class = f"risk-{bom_risk['color'].lower()}"
                        st.markdown(f"""
                        <div class="{color_class}">
                            <h3>RISCHIO BOM</h3>
                            <h1>{bom_risk['risk_level']}</h1>
                            <p>Score: {bom_risk['score']:.1f}/100</p>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        red_count = sum(1 for r in components_risk if r['color'] == 'RED')
                        st.metric("🔴 Componenti Alto Rischio", red_count)

                    with col3:
                        yellow_count = sum(1 for r in components_risk if r['color'] == 'YELLOW')
                        st.metric("🟡 Componenti Medio Rischio", yellow_count)

                    with col4:
                        total_man_hours = sum(r['man_hours'] for r in components_risk)
                        st.metric("⏱️ Man-Hours Stimati", f"{total_man_hours:,}h")

                    # Grafico distribuzione rischi
                    st.subheader("📈 Distribuzione Rischi")

                    col1, col2 = st.columns(2)

                    with col1:
                        # Pie chart
                        risk_counts = {
                            'Alto (RED)': sum(1 for r in components_risk if r['color'] == 'RED'),
                            'Medio (YELLOW)': sum(1 for r in components_risk if r['color'] == 'YELLOW'),
                            'Basso (GREEN)': sum(1 for r in components_risk if r['color'] == 'GREEN')
                        }

                        fig_pie = px.pie(
                            values=list(risk_counts.values()),
                            names=list(risk_counts.keys()),
                            color=list(risk_counts.keys()),
                            color_discrete_map={
                                'Alto (RED)': '#ff4444',
                                'Medio (YELLOW)': '#ffbb33',
                                'Basso (GREEN)': '#00C851'
                            },
                            title="Distribuzione per Livello di Rischio"
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)

                    with col2:
                        # Bar chart scores
                        fig_bar = go.Figure()

                        colors = ['#ff4444' if r['color'] == 'RED' else '#ffbb33' if r['color'] == 'YELLOW' else '#00C851'
                                  for r in components_risk]

                        fig_bar.add_trace(go.Bar(
                            x=[f"{r['supplier']}<br>{r['part_number']}" for r in components_risk],
                            y=[r['score'] for r in components_risk],
                            marker_color=colors,
                            text=[r['score'] for r in components_risk],
                            textposition='auto'
                        ))

                        fig_bar.add_hline(y=55, line_dash="dash", line_color="red", annotation_text="Soglia ALTO")
                        fig_bar.add_hline(y=30, line_dash="dash", line_color="orange", annotation_text="Soglia MEDIO")

                        fig_bar.update_layout(
                            title="Score Rischio per Componente",
                            xaxis_title="Componente",
                            yaxis_title="Risk Score",
                            showlegend=False
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)

                    # Dettaglio per componente
                    st.subheader("📝 Dettaglio Rischi per Componente")

                    # Ordina per rischio decrescente
                    sorted_risks = sorted(enumerate(components_risk), key=lambda x: x[1]['score'], reverse=True)

                    for idx, risk in sorted_risks:
                        color_emoji = "🔴" if risk['color'] == 'RED' else "🟡" if risk['color'] == 'YELLOW' else "🟢"

                        with st.expander(f"{color_emoji} **{risk['supplier']}** - {risk['part_number']} | Score: {risk['score']} | {risk['category']}", expanded=(risk['color'] == 'RED')):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.markdown("**🔍 Fattori di Rischio:**")
                                if risk['factors']:
                                    for factor in risk['factors']:
                                        st.markdown(f"- {factor}")
                                else:
                                    st.markdown("- Nessun fattore di rischio significativo")

                            with col2:
                                st.markdown("**💡 Suggerimenti:**")
                                if risk['suggestions']:
                                    for suggestion in risk['suggestions']:
                                        st.markdown(f"- {suggestion}")
                                else:
                                    st.markdown("- Nessuna azione richiesta")

                            st.markdown(f"**⏱️ Stima Man-Hours per mitigazione:** {risk['man_hours']}h")

                    # Export risultati
                    st.header("📥 Esporta Risultati")

                    # Prepara dataframe output
                    output_data = []
                    for i, risk in enumerate(components_risk):
                        output_data.append({
                            'Supplier': risk['supplier'],
                            'Part Number': risk['part_number'],
                            'Category': risk['category'],
                            'Risk Score': risk['score'],
                            'Risk Level': risk['risk_level'],
                            'Color Code': risk['color'],
                            'Risk Factors': ' | '.join(risk['factors']),
                            'Suggestions': ' | '.join(risk['suggestions']),
                            'Man-Hours Impact': risk['man_hours']
                        })

                    df_output = pd.DataFrame(output_data)

                    # Crea file Excel per download
                    output_buffer = BytesIO()
                    with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
                        # Foglio Summary
                        summary_data = {
                            'Metric': ['BOM Risk Level', 'BOM Risk Score', 'Total Components',
                                       'High Risk (RED)', 'Medium Risk (YELLOW)', 'Low Risk (GREEN)',
                                       'Total Man-Hours Estimated'],
                            'Value': [bom_risk['risk_level'], f"{bom_risk['score']:.1f}", len(components_risk),
                                      red_count, yellow_count, len(components_risk) - red_count - yellow_count,
                                      total_man_hours]
                        }
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

                        # Foglio dettaglio
                        df_output.to_excel(writer, sheet_name='Component Details', index=False)

                        # Formattazione
                        workbook = writer.book

                        # Formati colore
                        red_format = workbook.add_format({'bg_color': '#ff4444', 'font_color': 'white'})
                        yellow_format = workbook.add_format({'bg_color': '#ffbb33'})
                        green_format = workbook.add_format({'bg_color': '#00C851', 'font_color': 'white'})

                        worksheet = writer.sheets['Component Details']

                        # Applica formattazione condizionale
                        for row_num, risk in enumerate(components_risk, start=1):
                            if risk['color'] == 'RED':
                                worksheet.set_row(row_num, None, red_format)
                            elif risk['color'] == 'YELLOW':
                                worksheet.set_row(row_num, None, yellow_format)

                    st.download_button(
                        label="📥 Scarica Report Excel",
                        data=output_buffer.getvalue(),
                        file_name="supply_chain_risk_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    # Mostra tabella output
                    with st.expander("👁️ Anteprima Report", expanded=False):
                        st.dataframe(df_output, use_container_width=True)

                else:
                    st.error("❌ Non riesco a trovare l'header 'Supplier Name' nel foglio INPUTS")
            else:
                st.error("❌ Il file non contiene un foglio chiamato 'INPUTS'")
                st.info(f"Fogli trovati: {xl.sheet_names}")

        except Exception as e:
            st.error(f"❌ Errore nel caricamento del file: {str(e)}")
            st.exception(e)

    else:
        # Mostra istruzioni
        st.info("""
        👆 **Carica un file Excel** con il foglio 'INPUTS' contenente i dati dei componenti.

        Il file deve avere le seguenti colonne:
        - Supplier Name
        - Supplier Part Number
        - Unit Price ($)
        - How Many Device of this specific PN are in the BOM?
        - Category of product
        - Supplier Lead Time (weeks)
        - Country of Manufacturing Plant 1/2/3/4
        - Proprietary (Y/N)
        - Commodity (Y/N)
        - Stand-Alone Functional Device (Y/N)
        - Weeks to qualify
        - Buffer Stock Units
        - ... e altri
        """)

        # Download template
        st.subheader("📄 Scarica Template")
        st.markdown("Non hai un file? Scarica il template di esempio con 10 componenti:")

        # Questo bottone verrà gestito con il file che creeremo separatamente
        st.markdown("*Usa il file `BOM_Input_Template_10_Components.xlsx` generato insieme a questa app*")

# Fine tab1
with tab2:
    st.header("📊 Motore di Calcolo del Rischio")
    st.markdown("""
    Diagramma di flusso del motore di calcolo del rischio che mostra come viene calcolato
    il rischio per ogni componente e per l'intera BOM.
    """)

    # Leggi il file mermaid
    mermaid_file = Path(__file__).parent / "risk_engine_flow.mmd"
    if mermaid_file.exists():
        mermaid_code = mermaid_file.read_text(encoding="utf-8")

        # Usa components.html con mermaid.js (versione più vecchia e stabile)
        components.html(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@9.4.3/dist/mermaid.min.js"></script>
            <style>
                body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; background: white; }}
                .mermaid {{ background: white; padding: 20px; }}
            </style>
        </head>
        <body>
            <div class="mermaid" style="background: white;">
{mermaid_code}
            </div>
            <script>
                mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
            </script>
        </body>
        </html>
        """, height=1000, scrolling=True)
    else:
        st.warning("⚠️ File `risk_engine_flow.mmd` non trovato nella stessa cartella dell'app.")

with tab3:
    st.header("ℹ️ Guida all'uso")
    st.subheader("Come funziona l'analisi del rischio")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 1. Concentrazione Geografica (25%)
        - **CRITICO**: Tutti gli stabilimenti in un unico paese asiatico
        - **ALTO**: Tutti gli stabilimenti in Asia-Pacifico
        - **MEDIO**: Maggioranza degli stabilimenti in Asia

        ### 2. Single Source (20%)
        - **CRITICO**: Un solo stabilimento produttivo
        - **MEDIO**: Solo 2 stabilimenti produttivi

        ### 3. Lead Time (15%)
        - **CRITICO**: > 16 settimane
        - **ALTO**: > 10 settimane
        - **MEDIO**: > 6 settimane
        """)

    with col2:
        st.markdown("""
        ### 4. Buffer Stock (15%)
        - **CRITICO**: Buffer insufficiente a coprire il lead time
        - **MEDIO**: Buffer copre meno di 1.5x il lead time

        ### 5. Dipendenze (10%)
        - **ALTO**: Componente dipende da altri componenti

        ### 6. Proprietary/Commodity (10%)
        - **ALTO**: Componente proprietario
        - **MEDIO**: Componente non-commodity

        ### 7. Certificazioni (5%)
        - **MEDIO**: Riqualifica > 12 settimane
        """)

    st.markdown("---")
    st.subheader("Classificazione Finale")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="risk-red">
            <h3>🔴 ALTO</h3>
            <p>Score ≥ 55</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="risk-yellow">
            <h3>🟡 MEDIO</h3>
            <p>Score 30-54</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="risk-green">
            <h3>🟢 BASSO</h3>
            <p>Score < 30</p>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    Supply Chain Risk Assessment Tool v1.0 | 
    Basato su best practices per la gestione del rischio nella supply chain elettronica
</div>
""", unsafe_allow_html=True)
