# CLAUDE.md — Semiconductor Risk Manager

Questo file viene letto automaticamente da Claude Code ad ogni sessione.

---

## Come avviare l'app

```bash
python -m streamlit run app.py
```

> `streamlit run app.py` è bloccato dalla Windows Application Control Policy aziendale.
> Esiste un wrapper `C:\Users\danie\.local\bin\streamlit.cmd` che chiama `python -m streamlit %*`.

---

## Versione attuale: v4.0 (Supply Chain)

---

## Struttura progetto

```
app.py                    ← entry point Streamlit (aggiunge src/ al sys.path)
requirements.txt
data/
  part_numbers_db.xlsx    ← database principale (10 fogli)
  01_BOM_Input_Template_10.xlsx
  02_BOM_Automotive_ADAS_ECU_15.xlsx
  03_BOM_Industrial_IoT_Gateway_12.xlsx
src/
  tabs_modules.py         ← UI tutti i tab
  risk_engine.py          ← motore rischio (18 fattori)
  pn_lookup.py            ← CRUD Excel DB
  whatif_simulator.py     ← scenari What-If
  ems_risk.py             ← scoring EMS
  distributor_risk.py     ← scoring distributori
  tier2_visibility.py     ← Tier1→Tier2 linkage
  geo_risk.py             ← rischio geografico
  switching_cost.py       ← costo switching
  dependency_graph.py     ← grafi dipendenze
  pdf_export.py           ← export PDF
scripts/
  populate_sample_data.py
  create_bom_examples.py
  update_database_from_bom.py
docs/
  er_diagram.mmd
  platform_architecture.mmd
  supply_chain_gaps.mmd
```

---

## Database Excel — fogli disponibili

Aggiunti in v4.0:
- `EMS_Providers` — profili EMS
- `Distributors` — anagrafica distributori
- `Part_Distributors` — mapping PN↔distributore
- `Alt_Sources` — fonti alternative per PN
- `Supplier_Profiles` — profili fornitore JSON

---

## Modello di rischio — 18 fattori

- Fattori 1–15: rischio base (geo, lead time, sole source, ecc.)
- **Fattore 16**: EMS risk (+max 12 pt)
- **Fattore 17**: Distributor risk (+max 10 pt)
- **Fattore 18**: Hidden Single Source detection (+max 12 pt)

---

## Tab dell'app

1. Dashboard Esecutiva (con alert Hidden SPOF, mono-distributore, EMS critico)
2. Analisi Multipla (batch BOM)
3. Analisi Singola
4. **Filiera Commerciale** (nuovo v4.0)
   - Sub-tab: EMS Risk, Distributori, Hidden Single Source, Simulatore Stock-Out
5. What-If Simulator
6. Gestione Database
7. Guida

---

## Scenari What-If (12 predefiniti)

Tipi: `country_block`, `supplier_outage`, `lead_time_increase`, `demand_surge`,
`material_shortage`, `distributor_outage`, `ems_overload`

---

## Bug risolti

### "int object is not iterable" — Analisi Multipla BOM (RISOLTO)
- **File:** `risk_engine.py` righe 406–409
- **Causa:** Variable shadowing — `alt_sources` (parametro list) veniva sovrascritto
  dalla variabile locale `alt_sources` (int da colonna `Number_of_Alternative_Sources`)
- **Fix:** Variabile locale rinominata in `alt_sources_raw`

### Chiavi disallineate `_calculate_hidden_single_source` (RISOLTO)
- **File:** `risk_engine.py`
- **Fix:** Return dict allineato alle chiavi attese dalla UI:
  - `score` → `hidden_spof_score`
  - `converging_country` → `overlap_country`
  - `total_alts` → `total_sources`
  - aggiunta chiave `level` (`'CRITICO'`/`'ALTO'`/`'MEDIO'`/`'BASSO'`)
- `_calculate_hidden_single_source` ora gestisce input non-list in modo sicuro

---

## Note tecniche

- Encoding file: sempre `encoding='utf-8'` in tutti gli `open()`
- BOM di test: `02_BOM_Automotive_ADAS_ECU_15.xlsx` (15 part numbers)
- PowerShell profile: `C:\Users\danie\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`
- Lingua comunicazione con l'utente: **italiano**

---

## BOM Parser — qty e buffer stock (v4.1)

`render_tab_analisi_multipla()` in `tabs_modules.py` ora:
- Estrae **Run Rate** dall'intestazione BOM (riga con "run rate") → aggiorna `st.session_state.run_rate`
- Estrae **qty** (`How Many Device of this specific PN are in the BOM?`) e **buffer stock** (`If Dedicated Buffer Stock Units...`)
- Dopo batch analysis, salva in **Client_Data** via `db.add_part_number(pn, {qty, buf}, client_id=...)`
- Helper: `_extract_bom_client_data(df, pn_col)` e `_save_bom_client_data(qty_data, batch)`

---

## Roadmap / TODO

- Salvataggio storico analisi (trend per data)
- Estensione PDF export alle sezioni Filiera Commerciale
- Credenziali non hardcoded (per uso multi-utente)
