"""
guida.py — Tab: render_tab_guida
"""

import streamlit as st


def render_tab_guida():
    """Guide Tab: complete platform documentation v4.0"""

    st.title("Supply Chain Resilience Platform — v4.0")
    st.markdown(
        "B2B tool for proactive risk assessment and mitigation in the "
        "electronics supply chain. Covers the entire vertical supply chain: from Tier-2 materials "
        "all the way to the distribution channel."
    )

    st.markdown("---")

    # =========================================================================
    # ARCHITECTURE
    # =========================================================================
    st.header("Platform Architecture")

    st.markdown("""
The platform models **four supply chain levels** in an integrated way:

```
Tier-2/3 Materials          Neon gas, photoresists, wafer, rare earths, SiC...
        ↓
Tier-1 Supplier             STMicro, Infineon, NXP, TI, Renesas...
        ↓
EMS / Contract Mfg.         Foxconn, Flextronics, Jabil, in-house production...
        ↓
Distribution Channel        Arrow, Avnet, TTI, Digi-Key...
        ↓
Customer (BOM)              Electronic components in production
```

The **deterministic risk engine** aggregates 18 factors into a 0–100 score per component,
capped at 100 and classified HIGH/MEDIUM/LOW.
    """)

    st.markdown("---")

    # =========================================================================
    # AVAILABLE TABS
    # =========================================================================
    st.header("Platform Tabs")

    tab_docs = {
        "Multiple Analysis": "Load a BOM from an Excel file (or select an example) and run the batch analysis. "
                             "All subsequent tabs are populated from here. Supports .xlsx and .csv files with a 'Part Number' column.",
        "Executive Dashboard": "One-pager for management: main KPIs, category x risk level heat map, "
                               "top 10 at-risk components, commercial supply chain alerts (hidden SPOF, mono-distributor, critical EMS), "
                               "recommended actions by priority.",
        "Dependency Tree": "Directional graph of functional dependencies between components. "
                           "Identifies SPOFs, propagates risk along chains, calculates pair scores. "
                           "Requires NetworkX (pip install networkx).",
        "Geopolitical Map": "Displays Frontend (wafer fab) and Backend (assembly/test) geopolitical risks "
                            "on an interactive map. Country concentration heatmap and per-supplier analysis.",
        "Tier-2/3 Visibility": "Analyzes dependencies on critical upstream materials from Tier-1 suppliers "
                               "(neon gas, photoresists, wafer, rare earths, SiC, palladium, etc.). "
                               "With registered supplier profiles, uses fab-specific data instead of category defaults.",
        "Switching Costs": "Estimates man-hours to replace a component: SW porting, validation, certification. "
                           "Classification: TRIVIAL/MODERATE/COMPLEX/CRITICAL.",
        "Commercial Supply Chain": "**New v4.0** — EMS risk analysis, distributor risk, hidden single source detection, "
                                   "distributor stock-out simulator.",
        "What-If Simulator": "Simulates 12 predefined scenarios (Taiwan block, material shortages, distributor stock-out, "
                             "EMS overload, lead time increase). Calculates impact on buffer stock and financial impact.",
        "Database Management": "Full CRUD for all data: part numbers, clients, EMS providers, distributors, "
                               "alternative sources, supplier profiles. All data is entered here — never by editing Excel manually.",
    }

    for tab_name, description in tab_docs.items():
        with st.expander(f"**{tab_name}**"):
            st.markdown(description)

    st.markdown("---")

    # =========================================================================
    # SCORING MODEL — 18 FACTORS
    # =========================================================================
    st.header("Scoring Model — 18 Factors")
    st.markdown("Final score = sum of factors 1–18, capped at 100.")

    st.markdown("""
| # | Factor | Max | Supply chain level |
|---|--------|-----|--------------------|
| 1 | Geographic Concentration (Frontend/Backend) | 25 | Tier-1 Supplier |
| 2 | Single Source (production facilities) | 20 | Tier-1 Supplier |
| 3 | Lead Time | 15 | Tier-1 Supplier |
| 4 | Buffer Stock | −15 (reduction bonus) | Customer |
| 5 | Functional Dependencies (chain risk) | 10 | BOM |
| 6 | Proprietary / Commodity | 10 | Component |
| 7 | Required Certifications | 5 | Component |
| 8 | EOL Status | +15 | Tier-1 Supplier |
| 9 | Alternative Sources (no. of sources) | +10 / −3 | Market |
| 10 | Supplier Financial Health | +8 | Tier-1 Supplier |
| 11 | Allocation Status | +10 | Market |
| 12 | Price Increase (% last cycle) | +5 | Market |
| 13 | Package Type | +3 | Component |
| 14 | Technology Node | +5 | Wafer fab |
| 15 | Tier-2/3 Supply Chain | +15 | Tier-2 Materials |
| 16 | **EMS Risk** | **+12** | **EMS / Contract Mfg.** |
| 17 | **Distributor Risk** | **+10** | **Distribution Channel** |
| 18 | **Hidden Single Source** | **+12** | **Multi-sourcing** |
    """)

    st.markdown("---")

    # =========================================================================
    # NEW MODULES DETAIL v4.0
    # =========================================================================
    st.header("New Modules v4.0")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("EMS Risk (Factor 16 — max +12 pt)")
        st.markdown("""
Evaluates contract manufacturer/EMS risk across 6 dimensions:

| Sub-factor | Max |
|------------|-----|
| Financial health (A→D) | 15 pt |
| Capacity utilization (>95% = CRITICAL) | 15 pt |
| Backup sites (0 = single-site) | 12 pt |
| Geographic concentration | 15 pt |
| Certification gaps (IATF16949, ISO9001) | 10 pt |
| Years of activity (<5 years) | 5 pt |

EMS score capped at **30 pt**, contributes to the risk engine as +12 pt max.

If no complete EMS profile is available, only the geographic estimate from `EMS_Location` is used.
        """)

        st.subheader("Hidden Single Source (Factor 18 — max +12 pt)")
        st.markdown("""
Detects when all alternative sources for a component
converge on the same manufacturing country (Frontend_Country).

Example: 3 alternative suppliers all with fab in Taiwan
→ apparent diversification, real risk unchanged.

| Overlap ratio | Penalty | Level |
|---------------|---------|-------|
| 100% (all) | +12 pt | CRITICAL |
| ≥ 67% | +7 pt | HIGH |
| ≥ 50% | +4 pt | MEDIUM |

Requires alternative sources registered in **Database Management → Alternative Sources**.
        """)

    with col2:
        st.subheader("Distributor Risk (Factor 17 — max +10 pt)")
        st.markdown("""
Evaluates distribution channel risk across 5 dimensions:

| Sub-factor | Max |
|------------|-----|
| Mono-distributor (only 1 dist.) | 10 pt |
| Stock coverage < lead time | 8 pt |
| Distributor financial health | 10 pt |
| Lead time markup (additional weeks) | 5 pt |
| Distributor geographic concentration | 5 pt |

Distributor score capped at **25 pt**, contributes to the risk engine as +10 pt max.

If stock coverage ≥ 2× lead time → **bonus −2 pt** (large buffer).
        """)

        st.subheader("Tier1→Tier2 Supplier-Specific Linkage")
        st.markdown("""
Priority hierarchy for material dependencies:

1. **Component_Materials** custom (per-PN override)
2. **Supplier Profile** (Key_Materials_Override JSON from Database Management)
3. **Default** category + technology node

Allows distinguishing:
- STM32 (Agrate IT fab) → Shin-Etsu wafer (JP), not generic Taiwan
- NXP i.MX (TSMC fab) → Ukraine neon gas, Japan photoresists

Supplier profiles are entered in **Database Management → Supplier Profiles**.
        """)

    st.markdown("---")

    # =========================================================================
    # WHAT-IF SIMULATOR — SCENARIOS
    # =========================================================================
    st.header("What-If Simulator — Available Scenarios")

    st.markdown("""
| Type | Predefined scenarios | Impact logic |
|------|---------------------|--------------|
| `country_block` | Taiwan ×2, China ×1 | Risk multiplier + buffer impact |
| `lead_time_increase` | +50%, +100% | Proportional increase in lead time score |
| `material_shortage` | Neon gas, Photoresists, Rare earths, SiC | Match by material and country |
| `distributor_outage` | Arrow 4w, Avnet 6w | Proportional penalty for buffer/stockout gap |
| `ems_overload` | Generic 95% capacity | Proportional % score increase by overload level |

For each impacted component, the simulator calculates:
- Remaining buffer weeks after the disruption
- Adjusted risk score
- Estimated financial impact (lost production × run rate)
    """)

    st.markdown("---")

    # =========================================================================
    # DATABASE FIELDS
    # =========================================================================
    st.header("Database Fields — Accepted Values")

    st.markdown("**Part Numbers (main sheet)**")
    st.markdown("""
| Field | Values | Impact |
|-------|--------|--------|
| EOL_Status | Active, NRND, Last_Buy, EOL, Obsolete | Factor 8 (+0→+15) |
| Number_of_Alternative_Sources | 0, 1, 2, 3, ... | Factor 9 |
| Supplier_Financial_Health | A, B, C, D | Factor 10 |
| Allocation_Status | Normal, Constrained, Allocated | Factor 11 |
| Last_Price_Increase_Pct | numeric % | Factor 12 |
| Package_Type | QFP, BGA, WLCSP, QFN, SOP, DIP, CSP, FCBGA | Factor 13 |
| Technology_Node | e.g. 7nm, 28nm, 180nm | Factor 14 |
| Frontend_Country | Wafer fab country | Factor 1 + Hidden SPOF |
| Backend_Country | Assembly/test country | Factor 1 |
| EMS_Used | Y / N | Factor 16 |
| EMS_Name | EMS name (must match EMS_Providers) | Factor 16 |
| Automotive_Grade | None, AEC-Q100, AEC-Q101, AEC-Q200 | Switching multiplier |
    """)

    st.markdown("**Additional sheets (managed via UI)**")
    st.markdown("""
| Sheet | Key fields | Use |
|-------|-----------|-----|
| EMS_Providers | EMS_Name, Country, Financial_Health, Capacity_Utilization_Pct, Backup_Sites_Count, Certifications | Factor 16 full |
| Distributors | Name, Country, Financial_Health, Lead_Time_Markup_Weeks, Stock_Level_Weeks_Coverage | Factor 17 |
| Part_Distributors | Part_Number, Distributor_ID, Priority (Primary/Secondary), Allocation_Pct | PN↔Distributor link |
| Alt_Sources | Part_Number, Supplier_Name, Frontend_Country, Qualification_Status | Factor 18 Hidden SPOF |
| Supplier_Profiles | Supplier_Name, Primary_Fab, Primary_Fab_Country, Key_Materials_Override (JSON) | Tier1→Tier2 linkage |
    """)

    st.markdown("---")

    # =========================================================================
    # RECOMMENDED WORKFLOW
    # =========================================================================
    st.header("Recommended Workflow")

    st.markdown("""
**Initial setup** (once per client):
1. **Database Management → Client Management**: add the client and the default run rate
2. **Database Management → EMS Providers**: register the contract manufacturers used by components
3. **Database Management → Distributors**: register Arrow, Avnet, TTI, etc. and link them to Part Numbers
4. **Database Management → Alternative Sources**: for each critical PN, enter alternatives with `Frontend_Country`
5. **Database Management → Supplier Profiles**: for key suppliers (STM, NXP, Infineon...), specify fab and materials

**Recurring analysis** (for each BOM revision):
1. Sidebar: select the client
2. **Multiple Analysis**: load the BOM and start the analysis
3. **Executive Dashboard**: check KPIs and supply chain alerts
4. **Commercial Supply Chain**: EMS, distributor, hidden SPOF analysis
5. **What-If Simulator**: test disruption scenarios (Taiwan, distributor stock-out, EMS overload)
6. **Tier-2/3 Visibility**: check material bottlenecks
7. **Export**: generate PDF report for management
    """)

    st.markdown("---")

    # =========================================================================
    # CLASSIFICATION
    # =========================================================================
    st.subheader("Final Classification")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="risk-red"><h3>HIGH</h3><p>Score ≥ 55</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="risk-yellow"><h3>MEDIUM</h3><p>Score 30–54</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="risk-green"><h3>LOW</h3><p>Score &lt; 30</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================================
    # KNOWN LIMITATIONS AND ROADMAP
    # =========================================================================
    st.header("Known Limitations and Roadmap")
    st.markdown("""
| Limitation | Current workaround | Future development |
|------------|-------------------|-------------------|
| No historical trend | Static baseline in Dashboard | Save analysis by date |
| Partial EMS score without profile | Estimate from EMS_Location (geo only) | Automatic enrichment via API |
| Hardcoded login credentials | Secure for internal use | LDAP/SSO integration |
| PDF export does not cover Supply Chain tab | Export from Multiple Analysis tab | Extend pdf_export.py |
| No market data integration | Manual price and allocation entry | Octopart/SiliconExpert feed |
    """)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

