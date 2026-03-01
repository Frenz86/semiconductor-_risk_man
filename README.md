# Supply Chain Resilience Platform v4.1

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
| **Alternative Engine** | Compatibility score per fonti alternative (interfaccia, package, effort porting, market shortage) |
| **Costi di Switching** | Stima ore-uomo e costi di sostituzione componente, classificazione TRIVIALE / MODERATO / COMPLESSO / CRITICO |
| **Simulatore What-If** | Scenari di disruption: blocco paese, interruzione fornitore, aumento lead time, picco domanda, carenza materiale Tier-2 |
| **Gestione Database** | CRUD completo per Part Numbers, Clienti, Tier-2, EMS, distributori e profili fornitore |
| **Export PDF** | Report professionale esportabile con tutti i dati dell'analisi |

---

## IP/SW Dependencies Risk

**Novità v4.1:** Aggiunto rischio specifico per dipendenze software e IP proprietario.

Ogni Part Number può avere dipendenze su IP/SW critiche (es. driver periferiche, stack firmware, EDA tools). Il motore calcola un **IP Risk score (0–20)** basato su:

- **Maintenance Status**: Abandoned (+10) → Deprecated (+7) → Maintenance_Only (+4) → Active (0)
- **Vendor Lock-in**: IPs proprietarie dallo stesso vendor → penalità +3
- **Alternative Scarcity**: IPs senza alternative vendor → +2 per IP (max +5)

Questo score viene poi normalizzato a 0–10 e incluso nel **Fattore 19** del motore di rischio.

**Livelli di criticità:**
- **CRITICAL**: score >= 15 (IPs Abandoned)
- **HIGH**: score >= 8 (IPs Deprecated o vendor lock-in)
- **MEDIUM**: score >= 3
- **LOW**: score < 3

---

## Risk Engine

Il motore di rischio calcola uno **score 0–100** per ogni componente basato su 20 fattori (v4.1+).

### Fattori base (pesati) — Fattori 1–15

| Fattore | Peso | Dettaglio |
|---------|------|-----------|
| Concentrazione Geografica | 25% | Rischio Frontend (60%) + Backend (40%), scoring per paese |
| Single Source | 20% | Numero stabilimenti produttivi e fonti alternative |
| Lead Time | 15% | Soglie a 6, 10, 16 settimane |
| Buffer Stock | 15% | Copertura rispetto al lead time |
| Dipendenze Funzionali | 10% | Componente stand-alone vs. catena critica |
| Proprietarieta' | 10% | Commodity vs. proprietario/custom |
| Certificazioni | 5% | Tempo di riqualifica (AEC-Q100, IEC 61508, ecc.) |

### Fattori addizionali — Fattori 16–20

| Fattore | Punti Max | Dettaglio | Versione |
|---------|-----------|-----------|----------|
| EOL Status | +15 | Active / NRND / Last_Buy / EOL / Obsolete | v3.0+ |
| Alternative Sources | +10 / -3 | Fonti alternative sul mercato | v3.0+ |
| Salute Finanziaria Fornitore | +8 | Rating A / B / C / D | v3.0+ |
| Allocation Status | +10 | Normal / Constrained / Allocated | v3.0+ |
| Aumento Prezzo | +5 | Ultimo aumento % come segnale di tensione | v3.0+ |
| Package Type | +3 | Package avanzati (WLCSP, FCBGA, 3D) | v3.0+ |
| Technology Node | +5 | Nodi avanzati <= 7nm | v3.0+ |
| Tier-2/3 Supply Chain | +15 | Concentrazione materiali critici a monte | v3.0+ |
| **EMS Risk** (F16) | +12 | Rischio produttore a contratto (concentrazione, backup, audit) | v4.0+ |
| **Distributor Risk** (F17) | +10 | Rischio distributore (mono-distributore, stock, greymarket) | v4.0+ |
| **Hidden Single Source** (F18) | +12 | SPOF nascosto: fonti alternative convergono sullo stesso paese/fab | v4.0+ |
| **IP/SW Dependency Risk** (F19) | +10 | Rischio proprietary lock-in, IPs Abandoned/Deprecated (v4.1+) | **v4.1+** |
| **Market Shortage** (F20) | +8 | Penalita' per interfacce/materiali in shortage globale (Tight/Critical) | **v5.0+** |

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
│   ├── risk_engine.py            # Motore di calcolo rischio (18 fattori)
│   ├── alternative_engine.py     # Compatibility score per fonti alternative (v5.0)
│   ├── pn_lookup.py              # Database manager (Excel-based)
│   ├── geo_risk.py               # Rischio geopolitico Frontend/Backend
│   ├── switching_cost.py         # Calcolo costi di switching
│   ├── dependency_graph.py       # Grafi dipendenze e SPOF (NetworkX)
│   ├── whatif_simulator.py       # Simulazione scenari di disruption
│   ├── tier2_visibility.py       # Visibilita' Tier-2/3
│   ├── ems_risk.py               # Risk scoring EMS provider
│   ├── distributor_risk.py       # Risk scoring distributori
│   ├── pdf_export.py             # Generazione report PDF (ReportLab)
│   └── tabs/                     # Pacchetto UI (refactored da tabs_modules.py)
│       ├── __init__.py           # Facade: re-esporta tutte le render_tab_*
│       ├── _shared.py            # Componenti UI condivisi (badge, mermaid)
│       ├── analisi_rapida.py     # Analisi Singola PN
│       ├── analisi_multipla.py   # Analisi batch BOM
│       ├── dashboard.py          # Dashboard Esecutiva
│       ├── albero_dipendenze.py  # Albero Dipendenze (NetworkX)
│       ├── mappa_geopolitica.py  # Mappa Folium geopolitica
│       ├── tier2_visibility.py   # Visibilita' Tier-2/3
│       ├── costi_switching.py    # Costi di switching
│       ├── filiera_commerciale.py# Filiera Commerciale (EMS, distributori)
│       ├── whatif.py             # Simulatore What-If
│       ├── gestione_database.py  # CRUD database
│       └── guida.py              # Guida utente
│
├── scripts/
│   ├── populate_sample_data.py   # Popola il DB con dati di esempio
│   ├── create_bom_examples.py    # Genera i BOM Excel di esempio
│   ├── update_database_from_bom.py  # Importa BOM nel database
│   └── create_readme_sheet.py   # Aggiunge foglio README al DB Excel
│
└── docs/
    ├── er_diagram.mmd            # ER diagram (Mermaid)
    ├── platform_architecture.mmd
    ├── supply_chain_gaps.mmd
    ├── TODO_NEXT.txt
    └── competitor.txt
```

---

## Database Excel — 11 fogli

| Foglio | Contenuto | Versione |
|--------|-----------|----------|
| `Part_Numbers` | Repository globale componenti (38+ campi) | v1.0+ |
| `Client_Data` | Override per cliente: qty BOM, buffer stock, lead time custom | v2.0+ |
| `Clients` | Anagrafica clienti con run rate default | v1.0+ |
| `Tier2_Suppliers` | Fornitori Tier-2 custom (materiale, paese, market share, criticita') | v3.0+ |
| `Component_Materials` | Associazioni PN ↔ materiale Tier-2 custom | v3.0+ |
| `EMS_Providers` | Produttori a contratto (EMS/ODM) con risk score | v4.0+ |
| `Distributors` | Distributori autorizzati con risk score | v4.0+ |
| `Part_Distributors` | Associazioni PN ↔ distributore | v4.0+ |
| `Alt_Sources` | Fonti alternative (second source, cross-ref) | v4.0+ |
| `Supplier_Profiles` | Profili finanziari e operativi dei fornitori | v4.0+ |
| `IP_Dependencies` | Dipendenze IP/SW: firmware stack, driver, EDA tools, proprietary IPs | **v4.1+** |

### Schema `IP_Dependencies`

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `IP_Dep_ID` | String | ID univoco (es. IPD_001) |
| `Part_Number` | String (FK) | Part Number dipendente |
| `IP_Name` | String | Nome IP/SW (es. "USB3.0 PHY Stack") |
| `IP_Type` | Enum | Peripheral_Library / Firmware_Stack / RTOS / Driver / EDA_IP / Design_Kit / Protocol_Stack |
| `IP_Vendor` | String | Fornitore IP (es. "Synaptics", "ARM", "Cadence") |
| `License_Type` | Enum | Proprietary / Open_Source / Custom / BSD / MIT |
| `Maintenance_Status` | Enum | **Active** / Maintenance_Only / Deprecated / Abandoned |
| `Last_Release_Year` | Integer | Anno ultima release (es. 2024) |
| `Vendor_Alternatives` | Integer | N. vendor alternativi disponibili (0 = nessuno) |
| `Notes` | String | Descrizione aggiuntiva |
| `Created_at` | Timestamp | Data creazione record |
| `Updated_at` | Timestamp | Data ultimo aggiornamento |

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
- Salvataggio storico analisi (trend per data)
- Credenziali non hardcoded (per uso multi-utente)

### Media priorita'
- Estensione PDF export alle sezioni Filiera Commerciale
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
