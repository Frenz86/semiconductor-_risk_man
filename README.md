# 🔌 Supply Chain Risk Assessment Tool

## Descrizione
Applicazione Streamlit per valutare il rischio della supply chain per componenti elettronici.
Carica un file Excel con la tua BOM e ottieni automaticamente:
- Valutazione del rischio per ogni componente (🔴 Alto / 🟡 Medio / 🟢 Basso)
- Rischio complessivo della BOM
- Suggerimenti per mitigare i rischi
- Stima delle ore-uomo necessarie per la mitigazione
- Report esportabile in Excel


## Utilizzo

1. Avvia l'app con `streamlit run app.py`
2. Si aprirà il browser all'indirizzo `http://localhost:8501`
3. Trascina il file Excel `BOM_Input_Template_10_Components.xlsx` nell'area di upload
4. Visualizza i risultati dell'analisi
5. Scarica il report Excel con i risultati

## File inclusi

- `app.py` - Applicazione Streamlit principale
- `BOM_Input_Template_10_Components.xlsx` - Template Excel con 10 componenti di esempio
- `README.md` - Questo file

## Fattori di Rischio Valutati

| Fattore | Peso | Descrizione |
|---------|------|-------------|
| Concentrazione geografica | 25% | Stabilimenti tutti in Asia = rischio alto |
| Single source | 20% | Un solo stabilimento = rischio critico |
| Lead time | 15% | >16 settimane = rischio alto |
| Buffer stock | 15% | Copertura < lead time = rischio critico |
| Dipendenze | 10% | Componente dipende da altri nella BOM |
| Proprietario | 10% | Nessuna alternativa diretta |
| Certificazioni | 5% | Tempo riqualifica lungo |

## Livelli di Rischio

- 🔴 **ALTO** (score ≥ 55): Azione immediata richiesta
- 🟡 **MEDIO** (score 30-54): Monitoraggio e piano di mitigazione
- 🟢 **BASSO** (score < 30): Rischio accettabile

## Componenti di Esempio nel Template

Il file template include 10 componenti con diversi profili di rischio:

1. **NXP MCU** - Rischio ALTO (single source Taiwan)
2. **ST MPU** - Rischio MOLTO ALTO (proprietario, dipendenze)
3. **ST PMIC** - Rischio ALTO (dipendenza critica da MPU)
4. **Bosch Sensor** - Rischio MEDIO (dual source)
5. **ESP32 WiFi** - Rischio MEDIO-ALTO (certificazioni)
6. **Murata MLCC** - Rischio BASSO (commodity)
7. **TI DC-DC** - Rischio BASSO-MEDIO
8. **Samsung DDR** - Rischio ALTO (dipendenza, Asia)
9. **Infineon CAN** - Rischio BASSO (multi-source EU)
10. **TE Connector** - Rischio MOLTO BASSO (global multi-source)

## Personalizzazione

Puoi modificare i pesi e le soglie nel file `supply_chain_app.py`:
- Sezione `calculate_component_risk()` per i fattori di rischio
- Soglie colore: score ≥ 55 = RED, ≥ 30 = YELLOW, < 30 = GREEN

## Screenshot

L'app mostra:
- Dashboard con metriche principali
- Grafico a torta della distribuzione rischi
- Grafico a barre degli score per componente
- Dettaglio espandibile per ogni componente
- Export Excel formattato con colori

---
*Supply Chain Risk Assessment Tool v1.0*
