# 🔌 Supply Chain Risk Assessment Tool v2.0

## 🚀 Novità nella Versione 2.0

Il sistema è stato completamente riprogettato con una **nuova architettura basata su knowledge base dei Part Numbers**.

### Cosa cambia dalla v1.0?

| Caratteristica | v1.0 | v2.0 |
|----------------|------|------|
| Input | Upload Excel con tutti i dati | Inserimento solo Part Number |
| Lookup manuale | Ogni volta | Automatico dal database |
| Gestione dati | File Excel esterni | Database centralizzato |
| Multi-cliente | Non supportato | ✅ Supportato |
| Analisi rapida | No | ✅ Singolo PN |
| Inserimento PN | Manuale nel file Excel | ✅ Wizard guidato |

## Descrizione

Applicazione Streamlit per valutare il rischio della supply chain per componenti elettronici basata su una knowledge base dei Part Numbers.

**Funzionalità principali:**
- ⚡ **Analisi Rapida**: Inserisci un Part Number e ottieni subito la valutazione del rischio
- 📋 **Analisi Multipla**: Analizza più Part Numbers contemporaneamente
- 🗄️ **Database Centralizzato**: Tutti i dati dei componenti in un unico Excel
- 👥 **Multi-Cliente**: Dati specifici per cliente (qty BOM, buffer stock)
- 💡 **Suggerimenti**: Raccomandazioni automatiche per mitigare i rischi
- 📊 **Report**: Export Excel con risultati formattati

## Architettura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        STREAMLIT APP                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Analisi      │  │ Gestione     │  │ Visualizzazione      │ │
│  │ Rapida/Multi │  │ Database     │  │ Risultati            │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘ │
└─────────┼──────────────────┼──────────────────────────────────┘
          │                  │
          ▼                  ▼
    ┌──────────┐      ┌─────────────────────────────────────┐
    │   pn_    │      │     part_numbers_db.xlsx             │
    │  lookup  │      │  ┌─────────────┬─────────────────┐   │
    │  .py     │      │  │Part_Numbers │   Client_Data   │   │
    └────┬─────┘      │  │(dati globali)│(dati cliente)  │   │
         │            │  └─────────────┴─────────────────┘   │
         │            └─────────────────────────────────────┘
         ▼
    ┌─────────────────┐
    │  risk_engine.py │
    │  (calcolo       │
    │   rischio)      │
    └─────────────────┘
```

## File del Progetto

### Moduli Python
- **`app.py`** - Interfaccia Streamlit principale
- **`risk_engine.py`** - Motore di calcolo del rischio (puro Python, riutilizzabile)
- **`pn_lookup.py`** - Modulo per lookup e gestione del database

### Database
- **`part_numbers_db.xlsx`** - Database Excel con 3 fogli:
  - `Part_Numbers` - Dati globali dei componenti
  - `Client_Data` - Dati specifici per cliente
  - `Clients` - Anagrafica clienti

### Altri File
- **`risk_engine_flow.mmd`** - Diagramma di flusso dell'algoritmo (Mermaid)
- **`BOM_Input_Template_10_Components.xlsx`** - Template di esempio (legacy)

## Utilizzo Rapido

### 1. Installazione

```bash
pip install -r requirements.txt
```

### 2. Avvio

```bash
streamlit run app.py
```

L'app si aprirà all'indirizzo `http://localhost:8501`

### 3. Primo Uso

1. **Seleziona il Cliente** dalla sidebar
2. **Inserisci un Part Number** (es. `STM32MP157CAC3`)
3. Clicca **Analizza**
4. Visualizza i risultati con fattori di rischio e suggerimenti

### 4. Se il PN non esiste

Se un Part Number non è nel database, usa il **wizard di inserimento guidato**:
1. Compila i campi obbligatori (*)
2. Il sistema salverà automaticamente nel database
3. Il PN sarà disponibile per future analisi

## Fattori di Rischio Valutati

| Fattore | Peso | Soglie |
|---------|------|--------|
| **Concentrazione Geografica** | 25% | Tutti in 1 paese Asia: +25<br>Tutti in Asia: +20<br>Maggioranza Asia: +12 |
| **Single Source** | 20% | 1 stabilimento: +20<br>2 stabilimenti: +10 |
| **Lead Time** | 15% | >16 settimane: +15<br>>10 settimane: +10<br>>6 settimane: +5 |
| **Buffer Stock** | 15% | Copertura < lead time: +15<br>Copertura < 1.5x lead time: +8 |
| **Dipendenze** | 10% | Non stand-alone: +10 |
| **Proprietary** | 10% | Proprietario: +10<br>Non commodity: +5 |
| **Certificazioni** | 5% | Riqualifica >12 settimane: +5 |

## Livelli di Rischio

- 🔴 **ALTO** (score ≥ 55): Azione immediata richiesta
- 🟡 **MEDIO** (score 30-54): Monitoraggio e piano di mitigazione
- 🟢 **BASSO** (score < 30): Rischio accettabile

## Gestione del Database

### Struttura del Database

Il file `part_numbers_db.xlsx` contiene 3 fogli:

#### 1. Part_Numbers (Dati Globali)
Contiene i dati intrinseci del componente:
- Part Number (chiave univoca)
- Supplier Name
- Category (MCU, MPU, Sensor, etc.)
- Paesi di produzione (Plant 1-4)
- Lead Time standard
- Caratteristiche (Proprietary, Commodity, Stand-Alone)
- Prezzo, Certificazioni, etc.

#### 2. Client_Data (Dati Specifici Cliente)
Contiene dati che variano per cliente:
- Client_ID
- Part Number
- Qty in BOM
- Buffer Stock Units
- Custom Lead Time (opzionale, sovrascrive quello globale)
- Notes

#### 3. Clients (Anagrafica)
- Client_ID
- Client_Name
- Default_Run_Rate

### Popolamento Iniziale

Il database è già popolato con 10 componenti di esempio:
1. MKE02Z64VLD4 (NXP MCU)
2. STM32MP157CAC3 (ST MPU)
3. STPMIC1APQR (ST PMIC)
4. BME280 (Bosch Sensor)
5. ESP32-WROOM-32E (Espressif WiFi)
6. GRM155R71C104KA88D (Murata MLCC)
7. TPS62840DLCR (TI DC-DC)
8. K4B4G1646E-BYMA (Samsung DDR)
9. TLE9251VLE (Infineon CAN)
10. 1-84953-4 (TE Connector)

## API Programmatica

I moduli possono essere usati anche al di fuori di Streamlit:

```python
from pn_lookup import PartNumberDatabase
from risk_engine import calculate_component_risk

# Inizializza database
db = PartNumberDatabase('part_numbers_db.xlsx')

# Lookup part number
data = db.lookup_part_number('STM32MP157CAC3', client_id='DEMO_CLIENT')

# Calcola rischio
risk = calculate_component_risk(data, run_rate=5000)

print(f"Rischio: {risk['risk_level']} (Score: {risk['score']})")
print(f"Fattori: {risk['factors']}")
print(f"Suggerimenti: {risk['suggestions']}")
```

## Personalizzazione

### Modifica dei Pesi

Modifica le costanti in `risk_engine.py`:

```python
# Soglie di rischio
RISK_THRESHOLDS = {
    'high': 55,    # Score >= 55 -> RED
    'medium': 30   # Score >= 30 -> YELLOW
}

# Paesi ad alto rischio
HIGH_RISK_COUNTRIES = [
    'taiwan', 'china', 'korea', 'japan',
    'malaysia', 'singapore', 'philippines'
]
```

### Aggiunta di Nuovi Clienti

Dall'app: Tab "Gestione Database" → "Gestione Clienti"

Oppure via codice:

```python
db = PartNumberDatabase()
db.add_client('CLIENTE_001', 'Nome Cliente', default_run_rate=10000)
```

## Troubleshooting

### Errore: "Nessun cliente trovato"
Vai su "Gestione Database" → "Gestione Clienti" e aggiungi il primo cliente.

### Errore: "Part Number non trovato"
Usa il wizard di inserimento guidato o vai su "Gestione Database" → "Aggiungi Part Number".

### Database non sincronizzato
Se apporti modifiche manuali al file Excel, riavvia l'app.

## Roadmap

- [ ] Export PDF dei report
- [ ] API REST per integrazione esterna
- [ ] Dashboard trend temporali
- [ ] Notifiche EOL/PCN automatiche
- [ ] Integrazione con API distributori (DigiKey, Mouser, etc.)

## Changelog

### v2.0 (2024)
- Nuova architettura basata su knowledge base
- Lookup automatico dei Part Numbers
- Supporto multi-cliente
- Analisi rapida singolo PN
- Wizard di inserimento guidato
- Moduli Python riutilizzabili

### v1.0
- Upload Excel con BOM
- Analisi rischio multi-componente
- Export Excel con risultati

---

**Supply Chain Risk Assessment Tool v2.0** | Basato su knowledge base per analisi rapida del rischio
