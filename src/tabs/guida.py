"""
guida.py — Tab: render_tab_guida
"""

import streamlit as st


def render_tab_guida():
    """Tab Guida: documentazione completa della piattaforma v4.0"""

    st.title("Supply Chain Resilience Platform — v4.0")
    st.markdown(
        "Strumento B2B per la valutazione e mitigazione proattiva del rischio nella "
        "supply chain elettronica. Copre l'intera filiera verticale: dai materiali Tier-2 "
        "fino al canale distributivo."
    )

    st.markdown("---")

    # =========================================================================
    # ARCHITETTURA
    # =========================================================================
    st.header("Architettura della Piattaforma")

    st.markdown("""
La piattaforma modella **quattro livelli della supply chain** in modo integrato:

```
Materiali Tier-2/3          Neon gas, photoresists, wafer, terre rare, SiC...
        ↓
Fornitore Tier-1            STMicro, Infineon, NXP, TI, Renesas...
        ↓
EMS / Terzista              Foxconn, Flextronics, Jabil, produzione in house...
        ↓
Canale Distributivo         Arrow, Avnet, TTI, Digi-Key...
        ↓
Cliente (BOM)               Componenti elettronici in produzione
```

Il **risk engine deterministico** aggrega 18 fattori in uno score 0–100 per componente,
con cap a 100 e classificazione ALTO/MEDIO/BASSO.
    """)

    st.markdown("---")

    # =========================================================================
    # TAB DISPONIBILI
    # =========================================================================
    st.header("Tab della Piattaforma")

    tab_docs = {
        "Analisi Multipla": "Carica una BOM da file Excel (o seleziona un esempio) ed esegui l'analisi batch. "
                            "Tutti i tab successivi si popolano da qui. Supporta file .xlsx e .csv con colonna 'Part Number'.",
        "Dashboard Esecutiva": "One-pager per il management: KPI principali, heat map categorie × livello rischio, "
                               "top 10 componenti a rischio, alert filiera commerciale (hidden SPOF, mono-distributore, EMS critico), "
                               "azioni raccomandate per priorità.",
        "Albero Dipendenze": "Grafo direzionale delle dipendenze funzionali tra componenti. "
                             "Identifica SPOF, propaga il rischio lungo le catene, calcola score di coppia. "
                             "Richiede NetworkX (pip install networkx).",
        "Mappa Geopolitica": "Visualizza i rischi geopolitici Frontend (wafer fab) e Backend (assembly/test) "
                             "su mappa interattiva. Heatmap concentrazione paesi e analisi per fornitore.",
        "Tier-2/3 Visibility": "Analizza le dipendenze sui materiali critici a monte dei fornitori Tier-1 "
                               "(neon gas, photoresists, wafer, terre rare, SiC, palladio, ecc.). "
                               "Con profili fornitore registrati, usa dati fab-specifici invece dei default per categoria.",
        "Costi di Switching": "Stima le ore-uomo per sostituire un componente: porting SW, validazione, certificazione. "
                              "Classificazione TRIVIALE/MODERATO/COMPLESSO/CRITICO.",
        "Filiera Commerciale": "**Nuovo v4.0** — Analisi EMS risk, rischio distributore, hidden single source detection, "
                               "simulatore stock-out distributore.",
        "Simulatore What-If": "Simula 12 scenari predefiniti (blocco Taiwan, carenze materiali, stock-out distributore, "
                              "EMS overload, aumento lead time). Calcola impatto su buffer stock e impatto finanziario.",
        "Gestione Database": "CRUD completo per tutti i dati: part numbers, clienti, EMS providers, distributori, "
                             "fonti alternative, profili fornitore. Tutti i dati si inseriscono qui — mai modificando l'Excel manualmente.",
    }

    for tab_name, description in tab_docs.items():
        with st.expander(f"**{tab_name}**"):
            st.markdown(description)

    st.markdown("---")

    # =========================================================================
    # MODELLO DI SCORING — 18 FATTORI
    # =========================================================================
    st.header("Modello di Scoring — 18 Fattori")
    st.markdown("Score finale = somma fattori 1–18, capped a 100.")

    st.markdown("""
| # | Fattore | Max | Livello supply chain |
|---|---------|-----|----------------------|
| 1 | Concentrazione Geografica (Frontend/Backend) | 25 | Fornitore Tier-1 |
| 2 | Single Source (stabilimenti produttivi) | 20 | Fornitore Tier-1 |
| 3 | Lead Time | 15 | Fornitore Tier-1 |
| 4 | Buffer Stock | −15 (bonus riduzione) | Cliente |
| 5 | Dipendenze Funzionali (chain risk) | 10 | BOM |
| 6 | Proprietary / Commodity | 10 | Componente |
| 7 | Certificazioni richieste | 5 | Componente |
| 8 | EOL Status | +15 | Fornitore Tier-1 |
| 9 | Alternative Sources (n. fonti) | +10 / −3 | Mercato |
| 10 | Salute Finanziaria Fornitore | +8 | Fornitore Tier-1 |
| 11 | Allocation Status | +10 | Mercato |
| 12 | Aumento Prezzo (% ultimo ciclo) | +5 | Mercato |
| 13 | Package Type | +3 | Componente |
| 14 | Technology Node | +5 | Wafer fab |
| 15 | Tier-2/3 Supply Chain | +15 | Materiali Tier-2 |
| 16 | **EMS Risk** | **+12** | **EMS / Terzista** |
| 17 | **Distributor Risk** | **+10** | **Canale Distributivo** |
| 18 | **Hidden Single Source** | **+12** | **Multi-sourcing** |
    """)

    st.markdown("---")

    # =========================================================================
    # DETTAGLIO NUOVI MODULI v4.0
    # =========================================================================
    st.header("Nuovi Moduli v4.0")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("EMS Risk (Fattore 16 — max +12 pt)")
        st.markdown("""
Valuta il rischio del terzista/EMS su 6 dimensioni:

| Sub-fattore | Max |
|-------------|-----|
| Salute finanziaria (A→D) | 15 pt |
| Utilizzo capacità (>95% = CRITICO) | 15 pt |
| Siti di backup (0 = single-site) | 12 pt |
| Concentrazione geografica | 15 pt |
| Gap certificazioni (IATF16949, ISO9001) | 10 pt |
| Anni di attività (<5 anni) | 5 pt |

Score EMS cappato a **30 pt**, contribuisce al risk engine come +12 pt max.

Se non è disponibile un profilo EMS completo, viene usata solo la stima geografica dalla `EMS_Location`.
        """)

        st.subheader("Hidden Single Source (Fattore 18 — max +12 pt)")
        st.markdown("""
Rileva quando tutte le fonti alternative di un componente
convergono sullo stesso paese di fabbricazione (Frontend_Country).

Esempio: 3 fornitori alternativi tutti con fab in Taiwan
→ diversificazione apparente, rischio reale invariato.

| Overlap ratio | Penalità | Livello |
|---------------|----------|---------|
| 100% (tutte) | +12 pt | CRITICO |
| ≥ 67% | +7 pt | ALTO |
| ≥ 50% | +4 pt | MEDIO |

Richiede fonti alternative registrate in **Gestione Database → Fonti Alternative**.
        """)

    with col2:
        st.subheader("Distributor Risk (Fattore 17 — max +10 pt)")
        st.markdown("""
Valuta il rischio del canale distributivo su 5 dimensioni:

| Sub-fattore | Max |
|-------------|-----|
| Mono-distributore (solo 1 dist.) | 10 pt |
| Stock coverage < lead time | 8 pt |
| Salute finanziaria distributore | 10 pt |
| Lead time markup (settimane aggiuntive) | 5 pt |
| Concentrazione geografica distributore | 5 pt |

Score distributore cappato a **25 pt**, contribuisce al risk engine come +10 pt max.

Se stock coverage ≥ 2× lead time → **bonus −2 pt** (buffer ampio).
        """)

        st.subheader("Tier1→Tier2 Supplier-Specific Linkage")
        st.markdown("""
Gerarchia priorità per le dipendenze materiali:

1. **Component_Materials** custom (override per singolo PN)
2. **Profilo Fornitore** (Key_Materials_Override JSON da Gestione DB)
3. **Default** categoria + technology node

Permette di distinguere:
- STM32 (fab Agrate IT) → wafer Shin-Etsu (JP), non generici Taiwan
- NXP i.MX (fab TSMC) → neon gas Ucraina, photoresists Giappone

I profili fornitore si inseriscono in **Gestione Database → Profili Fornitore**.
        """)

    st.markdown("---")

    # =========================================================================
    # SIMULATORE WHAT-IF — SCENARI
    # =========================================================================
    st.header("Simulatore What-If — Scenari Disponibili")

    st.markdown("""
| Tipo | Scenari predefiniti | Logica impatto |
|------|--------------------|----|
| `country_block` | Taiwan ×2, China ×1 | Moltiplicatore rischio + impatto buffer |
| `lead_time_increase` | +50%, +100% | Aumento proporzionale score lead time |
| `material_shortage` | Neon gas, Photoresists, Terre rare, SiC | Match per materiale e paese |
| `distributor_outage` | Arrow 4w, Avnet 6w | Penalità proporzionale gap buffer/stockout |
| `ems_overload` | Generico 95% capacità | Aumento % score proporzionale a overload |

Il simulatore calcola per ogni componente impattato:
- Settimane di buffer rimanenti dopo la disruption
- Score di rischio aggiustato
- Impatto finanziario stimato (produzione persa × run rate)
    """)

    st.markdown("---")

    # =========================================================================
    # CAMPI DATABASE
    # =========================================================================
    st.header("Campi Database — Valori Ammessi")

    st.markdown("**Part Numbers (foglio principale)**")
    st.markdown("""
| Campo | Valori | Impatto |
|-------|--------|---------|
| EOL_Status | Active, NRND, Last_Buy, EOL, Obsolete | Fattore 8 (+0→+15) |
| Number_of_Alternative_Sources | 0, 1, 2, 3, ... | Fattore 9 |
| Supplier_Financial_Health | A, B, C, D | Fattore 10 |
| Allocation_Status | Normal, Constrained, Allocated | Fattore 11 |
| Last_Price_Increase_Pct | % numerico | Fattore 12 |
| Package_Type | QFP, BGA, WLCSP, QFN, SOP, DIP, CSP, FCBGA | Fattore 13 |
| Technology_Node | es. 7nm, 28nm, 180nm | Fattore 14 |
| Frontend_Country | Paese fab wafer | Fattore 1 + Hidden SPOF |
| Backend_Country | Paese assembly/test | Fattore 1 |
| EMS_Used | Y / N | Fattore 16 |
| EMS_Name | Nome EMS (deve corrispondere a EMS_Providers) | Fattore 16 |
| Automotive_Grade | None, AEC-Q100, AEC-Q101, AEC-Q200 | Moltiplicatore switching |
    """)

    st.markdown("**Fogli aggiuntivi (gestiti via UI)**")
    st.markdown("""
| Foglio | Campi chiave | Uso |
|--------|-------------|-----|
| EMS_Providers | EMS_Name, Country, Financial_Health, Capacity_Utilization_Pct, Backup_Sites_Count, Certifications | Fattore 16 completo |
| Distributors | Name, Country, Financial_Health, Lead_Time_Markup_Weeks, Stock_Level_Weeks_Coverage | Fattore 17 |
| Part_Distributors | Part_Number, Distributor_ID, Priority (Primary/Secondary), Allocation_Pct | Collegamento PN↔Distributore |
| Alt_Sources | Part_Number, Supplier_Name, Frontend_Country, Qualification_Status | Fattore 18 Hidden SPOF |
| Supplier_Profiles | Supplier_Name, Primary_Fab, Primary_Fab_Country, Key_Materials_Override (JSON) | Tier1→Tier2 linkage |
    """)

    st.markdown("---")

    # =========================================================================
    # FLUSSO DI LAVORO
    # =========================================================================
    st.header("Flusso di Lavoro Consigliato")

    st.markdown("""
**Setup iniziale** (una tantum per cliente):
1. **Gestione Database → Gestione Clienti**: aggiungi il cliente e il run rate default
2. **Gestione Database → EMS Providers**: registra i terzisti usati dai componenti
3. **Gestione Database → Distributori**: registra Arrow, Avnet, TTI, ecc. e associali ai Part Numbers
4. **Gestione Database → Fonti Alternative**: per ogni PN critico, inserisci le alternative con `Frontend_Country`
5. **Gestione Database → Profili Fornitore**: per fornitori chiave (STM, NXP, Infineon...), specifica fab e materiali

**Analisi ricorrente** (per ogni revisione BOM):
1. Sidebar: seleziona il cliente
2. **Analisi Multipla**: carica la BOM e avvia l'analisi
3. **Dashboard Esecutiva**: verifica KPI e alert filiera
4. **Filiera Commerciale**: analisi EMS, distributori, hidden SPOF
5. **Simulatore What-If**: testa scenari di disruption (Taiwan, stock-out distributore, EMS overload)
6. **Tier-2/3 Visibility**: verifica bottleneck materiali
7. **Export**: genera report PDF per il management
    """)

    st.markdown("---")

    # =========================================================================
    # CLASSIFICAZIONE
    # =========================================================================
    st.subheader("Classificazione Finale")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="risk-red"><h3>ALTO</h3><p>Score ≥ 55</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="risk-yellow"><h3>MEDIO</h3><p>Score 30–54</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="risk-green"><h3>BASSO</h3><p>Score &lt; 30</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================================
    # LIMITI NOTI
    # =========================================================================
    st.header("Limiti Noti e Roadmap")
    st.markdown("""
| Limite | Workaround attuale | Sviluppo futuro |
|--------|--------------------|-----------------|
| Nessun trend storico | Baseline statica nella Dashboard | Salvataggio analisi per data |
| EMS score parziale senza profilo | Stima da EMS_Location (geo only) | Arricchimento automatico via API |
| Credenziali login hardcoded | Sicure per uso interno | Integrazione LDAP/SSO |
| PDF export non copre tab Filiera | Export da tab Analisi Multipla | Estensione pdf_export.py |
| Nessuna integrazione dati di mercato | Inserimento manuale prezzi e allocation | Feed Octopart/SiliconExpert |
    """)

    st.markdown("---")
    st.subheader("Classificazione Finale")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="risk-red"><h3>ALTO</h3><p>Score >= 55</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="risk-yellow"><h3>MEDIO</h3><p>Score 30-54</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="risk-green"><h3>BASSO</h3><p>Score < 30</p></div>', unsafe_allow_html=True)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

