# Supply Chain Resilience Platform v4.0

Piattaforma per la **valutazione proattiva del rischio e della resilienza** della supply chain elettronica nel settore semiconduttori.

Analizza BOM (Bill of Materials) di schede elettroniche, calcola un risk score deterministico per ogni componente e genera report esecutivi con raccomandazioni operative.

---

## Funzionalità principali

| Modulo | Descrizione |
|--------|-------------|
| **Analisi Multipla** | Upload BOM da Excel/CSV, analisi batch con risk score individuale e aggregato, salvataggio automatico qty e buffer stock per cliente |
| **Dashboard Esecutiva** | Vista d'insieme con KPI, distribuzione rischio, Top-N componenti critici e heatmap |
| **Albero Dipendenze** | Grafo interattivo delle correlazioni funzionali tra componenti (es. MPU ← PMIC ← DDR) con chain risk propagation e rilevamento SPOF |
| **Mappa Geopolitica** | Mappa Folium con rischio stratificato Frontend (Wafer Fab) / Backend (Assembly/Test OSAT) per paese |
| **Tier-2/3 Visibility** | Analisi dipendenze a monte: materiali critici (neon, photoresists, silicon wafers, terre rare), heatmap concentrazione per paese |
| **Filiera Commerciale** | Visibilità su EMS provider, distributori e fonti alternative per ogni componente |
| **Costi di Switching** | Stima ore-uomo e costi di sostituzione componente, classificazione TRIVIALE / MODERATO / COMPLESSO / CRITICO |
| **Simulatore What-If** | Scenari di disruption: blocco paese, interruzione fornitore, aumento lead time, picco domanda, carenza materiale Tier-2 |
| **Gestione Database** | CRUD completo per Part Numbers, Clienti, Tier-2, EMS, distributori e profili fornitore |
| **Export PDF** | Report professionale esportabile con tutti i dati dell'analisi |

---

## Risk Engine

Il motore di rischio calcola uno **score 0–100** per ogni componente basato su 15 fattori.

### Fattori base (pesati)

| Fattore | Peso | Dettaglio |
|---------|------|-----------|
| Concentrazione Geografica | 25% | Rischio Frontend (60%) + Backend (40%), scoring per paese |
| Single Source | 20% | Numero stabilimenti produttivi e fonti alternative |
| Lead Time | 15% | Soglie a 6, 10, 16 settimane |
| Buffer Stock | 15% | Copertura rispetto al lead time |
| Dipendenze Funzionali | 10% | Componente stand-alone vs. catena critica |
| Proprietarieta' | 10% | Commodity vs. proprietario/custom |
| Certificazioni | 5% | Tempo di riqualifica (AEC-Q100, IEC 61508, ecc.) |

### Fattori addizionali

| Fattore | Punti Max | Dettaglio |
|---------|-----------|-----------|
| EOL Status | +15 | Active / NRND / Last_Buy / EOL / Obsolete |
| Alternative Sources | +10 / -3 | Fonti alternative sul mercato |
| Salute Finanziaria Fornitore | +8 | Rating A / B / C / D |
| Allocation Status | +10 | Normal / Constrained / Allocated |
| Aumento Prezzo | +5 | Ultimo aumento % come segnale di tensione |
| Package Type | +3 | Package avanzati (WLCSP, FCBGA, 3D) |
| Technology Node | +5 | Nodi avanzati <= 7nm |
| Tier-2/3 Supply Chain | +15 | Concentrazione materiali critici a monte |

**Soglie di rischio:**
- **ALTO** (rosso): score >= 55
- **MEDIO** (giallo): score 30–54
- **BASSO** (verde): score < 30

---

## Tier-2/3 Visibility

Il modulo analizza le dipendenze nascoste a monte dei fornitori Tier-1, mappando 13 materiali critici per l'industria dei semiconduttori:

| Materiale | Paese Dominante | Concentrazione | Criticita' |
|-----------|----------------|----------------|------------|
| Neon Gas | Ucraina / Russia | ~70% | CRITICAL |
| Photoresists | Giappone | ~90% | CRITICAL |
| Silicon Wafers | Giappone | ~55% | CRITICAL |
| Rare Earth Elements | Cina | ~70% | HIGH |
| Palladium Wire | Sudafrica / Russia | ~65% | MEDIUM |
| SiC Substrates | USA | ~60% | HIGH |
| CMP Slurry | USA | ~45% | HIGH |
| GaN Substrates | Giappone | ~40% | HIGH |

**Approccio ibrido:** mappatura automatica per categoria + nodo tecnologico, con possibilita' di aggiungere fornitori Tier-2 custom nel database.

---

## Struttura del progetto

```
semiconductor_risk_man/
├── app.py                        # Entry point Streamlit
├── requirements.txt
│
├── data/
│   ├── part_numbers_db.xlsx      # Database principale (10 fogli)
│   ├── 01_BOM_Input_Template_10.xlsx
│   ├── 02_BOM_Automotive_ADAS_ECU_15.xlsx
│   └── 03_BOM_Industrial_IoT_Gateway_12.xlsx
│
├── src/
│   ├── risk_engine.py            # Motore di calcolo rischio
│   ├── pn_lookup.py              # Database manager (Excel-based)
│   ├── geo_risk.py               # Rischio geopolitico Frontend/Backend
│   ├── switching_cost.py         # Calcolo costi di switching
│   ├── dependency_graph.py       # Grafi dipendenze e SPOF (NetworkX)
│   ├── whatif_simulator.py       # Simulazione scenari di disruption
│   ├── tier2_visibility.py       # Visibilita' Tier-2/3
│   ├── ems_risk.py               # Risk scoring EMS provider
│   ├── distributor_risk.py       # Risk scoring distributori
│   ├── pdf_export.py             # Generazione report PDF (ReportLab)
│   └── tabs/
│       ├── __init__.py           # Facade: re-esporta tutte le render_tab_*
│       ├── _shared.py            # Componenti UI condivisi (badge, mermaid)
│       ├── analisi_rapida.py
│       ├── analisi_multipla.py
│       ├── dashboard.py
│       ├── albero_dipendenze.py
│       ├── mappa_geopolitica.py
│       ├── tier2_visibility.py
│       ├── costi_switching.py
│       ├── filiera_commerciale.py
│       ├── whatif.py
│       ├── gestione_database.py
│       └── guida.py
│
├── scripts/
│   ├── populate_sample_data.py   # Popola il DB con dati di esempio
│   ├── create_bom_examples.py    # Genera i BOM Excel di esempio
│   └── update_database_from_bom.py  # Importa BOM nel database
│
└── docs/
    ├── er_diagram.mmd            # ER diagram (Mermaid)
    ├── platform_architecture.mmd
    ├── supply_chain_gaps.mmd
    ├── TODO_NEXT.txt
    └── competitor.txt
```

---

## Database Excel — 10 fogli

| Foglio | Contenuto |
|--------|-----------|
| `Part_Numbers` | Repository globale componenti (38+ campi) |
| `Client_Data` | Override per cliente: qty BOM, buffer stock, lead time custom |
| `Clients` | Anagrafica clienti con run rate default |
| `Tier2_Suppliers` | Fornitori Tier-2 custom (materiale, paese, market share, criticita') |
| `Component_Materials` | Associazioni PN ↔ materiale Tier-2 custom |
| `EMS_Providers` | Produttori a contratto (EMS/ODM) con risk score |
| `Distributors` | Distributori autorizzati con risk score |
| `Part_Distributors` | Associazioni PN ↔ distributore |
| `Alt_Sources` | Fonti alternative (second source, cross-ref) |
| `Supplier_Profiles` | Profili finanziari e operativi dei fornitori |

---

## BOM di esempio

Il repository include BOM precompilati per testing immediato:

| File | Descrizione | PN |
|------|-------------|-----|
| `01_BOM_Input_Template_10.xlsx` | Template generico | 10 |
| `02_BOM_Automotive_ADAS_ECU_15.xlsx` | ECU ADAS automotive | 15 |
| `03_BOM_Industrial_IoT_Gateway_12.xlsx` | Gateway IoT industriale | 12 |

**Formato BOM** (3 colonne):

| Colonna | Descrizione |
|---------|-------------|
| `Supplier Part Number` | Part number del fornitore |
| `How Many Device of this specific PN are in the BOM?` | Quantita' per PCB |
| `If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units` | Buffer stock dedicato |

Riga di intestazione opzionale: `Run Rate (Number of PCB per week)` per impostare il run rate del cliente.

---

## Installazione e avvio

```bash
# Clona il repository
git clone <url-repo>
cd semiconductor_risk_man

# Crea un virtual environment (consigliato)
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

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

## Roadmap

### Alta priorita'
- Integrazione **Nexar API** per inventory e pricing real-time
- **EOL/PCN Alert System** — monitoraggio end-of-life e product change notice
- **Second Source Qualification Matrix**

### Media priorita'
- Safety stock dinamico con formula statistica (Z × sigma × sqrt(LT))
- Supplier Scorecard con KPI quantitativi (OTD, Quality PPM, financial health)
- Compliance & Sanctions (ITAR, EAR, OFAC, REACH, Conflict Minerals)

### Bassa priorita'
- Simulazione Monte Carlo per risk score probabilistico
- REST API per integrazione ERP / PLM / MES
- Recovery Curve Modeling post-disruption

---

## Licenza

Progetto proprietario. Tutti i diritti riservati.
