# Supply Chain Resilience Platform v3.2

Piattaforma per la **valutazione proattiva del rischio e della resilienza** della supply chain elettronica nel settore semiconduttori.

Analizza BOM (Bill of Materials) di schede elettroniche, calcola un risk score deterministico per ogni componente e genera report esecutivi con raccomandazioni operative.

---

## Funzionalità principali

| Modulo | Descrizione |
|--------|-------------|
| **Analisi Multipla** | Upload BOM da Excel/CSV, analisi batch di tutti i Part Number con risk score individuale e aggregato |
| **Dashboard Esecutiva** | Vista d'insieme con KPI, distribuzione rischio, Top-N componenti critici e heatmap |
| **Albero Dipendenze** | Grafo interattivo delle correlazioni funzionali tra componenti (es. MPU ← PMIC ← DDR) con chain risk propagation e rilevamento SPOF (Single Point of Failure) |
| **Mappa Geopolitica** | Mappa Folium con rischio stratificato Frontend (Wafer Fab) / Backend (Assembly/Test OSAT) per paese |
| **Tier-2/3 Visibility** | Analisi dipendenze a monte: materiali critici (neon gas, photoresists, silicon wafers, terre rare), heatmap concentrazione per paese, gestione fornitori custom |
| **Costi di Switching** | Stima ore-uomo e costi di sostituzione componente, classificazione TRIVIALE / MODERATO / COMPLESSO / CRITICO |
| **Simulatore What-If** | Scenari di disruption: blocco paese, interruzione fornitore, aumento lead time, picco domanda, carenza materiale Tier-2 — con impatto finanziario |
| **Gestione Database** | CRUD completo per Part Numbers, Clienti, fornitori Tier-2 e override dati per cliente |
| **Export PDF** | Report professionale esportabile con tutti i dati dell'analisi |

---

## Risk Engine

Il motore di rischio calcola uno **score 0–100** per ogni componente, basato su 15 fattori:

### Fattori base (pesati)

| Fattore | Peso | Dettaglio |
|---------|------|-----------|
| Concentrazione Geografica | 25% | Rischio Frontend (60%) + Backend (40%), con scoring per paese |
| Single Source | 20% | Numero di stabilimenti produttivi e fornitori alternativi |
| Lead Time | 15% | Soglie a 6, 10, 16 settimane |
| Buffer Stock | 15% | Copertura rispetto al lead time, riduzione proporzionale del rischio |
| Dipendenze Funzionali | 10% | Componente stand-alone vs. catena critica |
| Proprietarieta' | 10% | Commodity vs. proprietario/custom |
| Certificazioni | 5% | Tempo di riqualifica (AEC-Q100, IEC 61508, ecc.) |

### Fattori addizionali

| Fattore | Punti Max | Dettaglio |
|---------|-----------|-----------|
| EOL Status | +15 | Active / NRND / Last_Buy / EOL / Obsolete |
| Alternative Sources | +10 / -3 | Fonti alternative sul mercato |
| Salute Finanziaria Fornitore | +8 | Rating A/B/C/D |
| Allocation Status | +10 | Normal / Constrained / Allocated |
| Aumento Prezzo | +5 | Ultimo aumento % come segnale di tensione |
| Package Type | +3 | Package avanzati (WLCSP, FCBGA, 3D) |
| Technology Node | +5 | Nodi avanzati <= 7nm |
| **Tier-2/3 Supply Chain** | **+15** | Concentrazione materiali critici a monte (neon, wafer, photoresists) |

**Soglie di rischio:**
- **ALTO** (rosso): score >= 55
- **MEDIO** (giallo): score 30–54
- **BASSO** (verde): score < 30

---

## Tier-2/3 Supply Chain Visibility

Il modulo analizza le dipendenze nascoste a monte dei fornitori Tier-1, identificando 13 materiali critici per l'industria dei semiconduttori:

| Materiale | Paese Dominante | Concentrazione | Criticita' |
|-----------|----------------|----------------|------------|
| Neon Gas | Ucraina/Russia | ~70% | CRITICAL |
| Photoresists | Giappone | ~90% | CRITICAL |
| Silicon Wafers | Giappone | ~55% | CRITICAL |
| Rare Earth Elements | Cina | ~70% | HIGH |
| Palladium Wire | Sudafrica/Russia | ~65% | MEDIUM |
| SiC Substrates | USA | ~60% | HIGH |
| Sapphire Substrates | Cina | ~50% | MEDIUM |
| CMP Slurry | USA | ~45% | HIGH |
| GaN Substrates | Giappone | ~40% | HIGH |

**Approccio ibrido:**
- **Predefinito**: ogni combinazione categoria (MCU, MPU, Sensor, Power...) + nodo tecnologico (advanced/mainstream/mature/legacy) e' automaticamente mappata ai materiali critici necessari
- **Custom**: possibilita' di aggiungere fornitori Tier-2 e associazioni materiale-componente nel database

**Scoring** (0–25, scalato a 0–15 nel risk score finale):
- Concentrazione materiale per paese (0-10)
- Numero materiali critici/non-sostituibili (0-5)
- Overlap geopolitico frontend/Tier-2 (0-5)
- Penalita' nodo avanzato (0-5)

---

## Architettura

```
app.py                      # Entry point Streamlit, routing tab, login
├── tabs_modules.py          # Rendering UI di tutti i tab
├── risk_engine.py           # Motore di calcolo rischio (business logic pura)
├── tier2_visibility.py      # Visibilita' Tier-2/3 supply chain (materiali critici)
├── pn_lookup.py             # Database manager (Excel-based, 5 fogli)
├── geo_risk.py              # Rischio geopolitico Frontend/Backend per paese
├── switching_cost.py        # Calcolo costi di switching componente
├── dependency_graph.py      # Grafi di dipendenza e SPOF detection (NetworkX)
├── whatif_simulator.py      # Simulazione scenari di disruption
├── pdf_export.py            # Generazione report PDF (ReportLab)
├── create_bom_examples.py   # Script per generare BOM di esempio
├── update_database_from_bom.py  # Import BOM in database
├── part_numbers_db.xlsx     # Database principale (5 fogli)
├── NEXARAPI/                # Modulo Nexar API (integrazione futura)
└── *.xlsx                   # BOM di esempio (Automotive ADAS, IoT Gateway, ecc.)
```

### Database Excel (5 fogli)

| Foglio | Contenuto |
|--------|-----------|
| `Part_Numbers` | Repository globale componenti (38+ campi) |
| `Client_Data` | Override specifici per cliente (buffer, lead time, qty BOM) |
| `Clients` | Anagrafica clienti |
| `Tier2_Suppliers` | Fornitori Tier-2 custom (nome, materiale, paese, market share, criticita') |
| `Component_Materials` | Associazioni PN ↔ materiale Tier-2 custom |

---

## Requisiti

- Python 3.10+
- Dipendenze: vedi [requirements.txt](requirements.txt)

```
streamlit>=1.38.0
pandas>=2.0.0
openpyxl>=3.1.0
xlsxwriter>=3.1.0
plotly>=5.18.0
streamlit-folium>=0.23.0
folium>=0.18.0
networkx>=3.0
matplotlib>=3.7.0
reportlab>=4.0.0
```

---

## Installazione e avvio

```bash
# Clona il repository
git clone <url-repo>
cd semiconductor_risk_man

# Crea un virtual environment (consigliato)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installa le dipendenze
pip install -r requirements.txt

# Avvia l'applicazione
streamlit run app.py
```

L'applicazione sara' disponibile su `http://localhost:8501`.

### Credenziali di default

| Username | Password |
|----------|----------|
| `admin`  | `admin`  |
| `user`   | `admin`  |
| `guest`  | `guest`  |

---

## BOM di esempio inclusi

Il repository include BOM precompilati per testing:

- **01_BOM_Input_Template_10.xlsx** — Template generico con 10 componenti
- **02_BOM_Automotive_ADAS_ECU_15.xlsx** — ECU ADAS automotive con 15 componenti
- **03_BOM_Industrial_IoT_Gateway_12.xlsx** — Gateway IoT industriale con 12 componenti

---

## Roadmap

### Alta priorita
- Integrazione **Nexar API** per inventory e pricing real-time
- **EOL/PCN Alert System** per monitoraggio end-of-life e product change notice
- **Second Source Qualification Matrix**

### Media priorita
- Safety stock dinamico con formula statistica (Z x sigma x sqrt(LT))
- Supplier Scorecard con KPI quantitativi (OTD, Quality PPM, financial health)
- Compliance & Sanctions (ITAR, EAR, OFAC, REACH, Conflict Minerals)

### Bassa priorita
- Simulazione Monte Carlo per risk score probabilistico
- REST API per integrazione ERP/PLM/MES
- Recovery Curve Modeling post-disruption

---

## Stack tecnologico

| Componente | Tecnologia |
|------------|------------|
| Frontend | Streamlit |
| Visualizzazione | Plotly, Folium, Mermaid.js |
| Grafi | NetworkX |
| Database | Excel (openpyxl) |
| Report | ReportLab (PDF) |
| Mappe | Folium + streamlit-folium |

---

## Licenza

Progetto proprietario. Tutti i diritti riservati.
