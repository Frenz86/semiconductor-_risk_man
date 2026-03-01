"""
create_readme_sheet.py — Adds a README data-dictionary tab as the first sheet
in data/part_numbers_db.xlsx documenting all 11 sheets and their columns.
"""
import sys
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "part_numbers_db.xlsx"

# ─── Styles ───────────────────────────────────────────────────────────────────
font_title  = Font(name="Calibri", bold=True, size=16, color="FFFFFF")
font_sheet  = Font(name="Calibri", bold=True, size=12, color="FFFFFF")
font_colhdr = Font(name="Calibri", bold=True, size=10, color="FFFFFF")
font_req    = Font(name="Calibri", size=10, bold=True)
font_normal = Font(name="Calibri", size=10)

fill_title  = PatternFill("solid", fgColor="1F3864")
fill_sheet  = PatternFill("solid", fgColor="2E75B6")
fill_colhdr = PatternFill("solid", fgColor="2F5496")
fill_req    = PatternFill("solid", fgColor="FFF2CC")
fill_auto   = PatternFill("solid", fgColor="E2EFDA")
fill_opt    = PatternFill("solid", fgColor="F2F2F2")
fill_header = PatternFill("solid", fgColor="D6E4F0")

thin   = Side(style="thin", color="AAAAAA")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
align_wrap   = Alignment(horizontal="left",   vertical="top",    wrap_text=True)
align_left   = Alignment(horizontal="left",   vertical="center")

ROW = 0  # module-level row counter

def _cell(ws, r, c, value, font=None, fill=None, alignment=None):
    cell = ws.cell(row=r, column=c, value=value)
    if font:      cell.font      = font
    if fill:      cell.fill      = fill
    if alignment: cell.alignment = alignment
    cell.border = border
    return cell

def _merge(ws, r, c1, c2, value, font, fill, align=None):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    cell = ws.cell(row=r, column=c1, value=value)
    cell.font      = font
    cell.fill      = fill
    cell.border    = border
    cell.alignment = align or align_center
    return cell


def build_readme(wb):
    global ROW
    ROW = 0

    if "README" in wb.sheetnames:
        del wb["README"]

    ws = wb.create_sheet("README", 0)

    # Column widths
    for col, w in {1: 33, 2: 18, 3: 54, 4: 10, 5: 30}.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    # ── Title ──────────────────────────────────────────────────────────────
    ROW = 1
    _merge(ws, ROW, 1, 5,
           "Semiconductor Supply Chain Risk Manager — Database Reference (v5.0)",
           font_title, fill_title)
    ws.row_dimensions[ROW].height = 30

    ROW = 2
    _merge(ws, ROW, 1, 5,
           "This sheet documents all tables (Excel sheets) and their columns.  "
           "Required = Y means the risk engine may return wrong results if empty.  "
           "Auto = computed / auto-filled by the application.",
           font_normal, fill_header, align_wrap)
    ws.row_dimensions[ROW].height = 40

    ROW = 3
    for c, hdr in enumerate(
        ["Field Name", "Type / Allowed Values", "Description", "Required", "Used In (Risk Factor)"], 1
    ):
        _cell(ws, ROW, c, hdr, font=font_colhdr, fill=fill_colhdr, alignment=align_center)
    ws.row_dimensions[ROW].height = 18

    # ── Section helper ──────────────────────────────────────────────────────
    def section(title, fields):
        global ROW
        ROW += 1
        _merge(ws, ROW, 1, 5, f"  {title}", font_sheet, fill_sheet)
        ws.row_dimensions[ROW].height = 20

        for name, type_vals, description, required, risk_factor in fields:
            ROW += 1
            if required == "Y":
                fill, fnt = fill_req, font_req
            elif required == "Auto":
                fill, fnt = fill_auto, font_normal
            else:
                fill, fnt = fill_opt, font_normal

            _cell(ws, ROW, 1, name,        font=fnt,        fill=fill, alignment=align_left)
            _cell(ws, ROW, 2, type_vals,   font=font_normal, fill=fill, alignment=align_wrap)
            _cell(ws, ROW, 3, description, font=font_normal, fill=fill, alignment=align_wrap)
            _cell(ws, ROW, 4, required,    font=font_normal, fill=fill, alignment=align_center)
            _cell(ws, ROW, 5, risk_factor, font=font_normal, fill=fill, alignment=align_wrap)
            ws.row_dimensions[ROW].height = 34

    # ══════════════════════════════════════════════════════════════════════
    # 1 · Part_Numbers
    # ══════════════════════════════════════════════════════════════════════
    section("1 · Part_Numbers — Global component repository", [
        ("Part_Number",
         "Text (unique PK)",
         "Primary key. Manufacturer part number exactly as printed on the package.",
         "Y", "All factors"),
        ("Description",
         "Text",
         "Short human-readable description (e.g. ARM Cortex-A53 MPU 64-bit).",
         "Y", "Display only"),
        ("Manufacturer",
         "Text",
         "Silicon vendor name (NXP, TI, Renesas, Samsung, Infineon…).",
         "Y", "Factor 6 – Sole Source"),
        ("Category",
         "MPU | MCU | Memory | PMIC | Sensor | Passive | Other",
         "Component category. Used to select Tier-2 material mapping and dependency-graph icons.",
         "Y", "Factor 14 – Tier-2 Visibility"),
        ("Technology_Node_nm",
         "Integer (nm)",
         "Process node in nanometres (7, 14, 28, 65, 130…). Node ≤ 7 nm adds +5 risk points.",
         "N", "Factor 15 – Technology Node"),
        ("Package_Type",
         "BGA | QFN | QFP | WLCSP | FCBGA | 3D-IC | DIP | SOT | SOP | Other",
         "Physical package. Advanced packages (WLCSP, FCBGA, 3D-IC) add +3 risk points.",
         "N", "Factor 13 – Package Type"),
        ("EOL_Status",
         "Active | NRND | Last_Buy | EOL | Obsolete",
         "Product lifecycle status. Obsolete = +15 pt; EOL = +15 pt; Last_Buy = +12 pt; NRND = +8 pt.",
         "Y", "Factor 8 – EOL Status"),
        ("Lead_Time_Weeks",
         "Integer (weeks)",
         "Standard manufacturer lead time in weeks. > 16 wk = +15 pt; 10–16 wk = +10 pt; 6–10 wk = +5 pt.",
         "Y", "Factor 3 – Lead Time"),
        ("Frontend_Country",
         "ISO country name (Taiwan, Japan, South Korea, USA, China…)",
         "Country where the wafer fab (frontend) is located. Drives geopolitical risk score (60 % weight of geo factor).",
         "Y", "Factor 1 – Geo Risk"),
        ("Backend_Country",
         "ISO country name",
         "Country where packaging / test (OSAT backend) is performed (40 % weight of geo factor).",
         "Y", "Factor 1 – Geo Risk"),
        ("Number_of_Fabs",
         "Integer",
         "Number of distinct wafer fabs producing this PN. 1 = single-source risk (+20 pt).",
         "Y", "Factor 2 – Single Source"),
        ("Number_of_Alternative_Sources",
         "Integer",
         "Count of qualified second-source / cross-reference components. 0 = +10 pt; >= 3 = -3 pt.",
         "Y", "Factor 9 – Alternative Sources"),
        ("Proprietary",
         "Y | N",
         "Y if the component is custom / proprietary (no drop-in alternative exists). Adds +10 pt.",
         "Y", "Factor 7 – Proprietary"),
        ("Functional_Dependencies",
         "Comma-separated PN list (e.g. PN-002,PN-007)",
         "Part numbers that this component functionally depends on. Used by the Dependency Graph to compute chain risk and detect SPOFs.",
         "N", "Factor 5 – Functional Dependencies"),
        ("Certification_Months",
         "Integer (months)",
         "Estimated re-qualification time if this component is replaced. > 18 mo = +5 pt; 12–18 = +3 pt; 6–12 = +1 pt.",
         "N", "Factor 6 – Certification"),
        ("Financial_Health",
         "A | B | C | D",
         "Supplier financial health rating. D = +8 pt; C = +5 pt; B = +2 pt; A = 0 pt.",
         "N", "Factor 10 – Financial Health"),
        ("Allocation_Status",
         "Normal | Constrained | Allocated",
         "Current allocation status from the manufacturer. Allocated = +10 pt; Constrained = +5 pt.",
         "N", "Factor 11 – Allocation"),
        ("Last_Price_Increase_Pct",
         "Float (%)",
         "Last reported price increase percentage — used as market-tension signal. > 20 % = +5 pt.",
         "N", "Factor 12 – Price Increase"),
        ("Memory_Type",
         "DDR3 | DDR4 | DDR5 | LPDDR4 | LPDDR4X | LPDDR5 | NOR_Flash | NAND_Flash | SRAM | other",
         "Legacy field for memory interface type. For processors, prefer Supported_Interfaces.",
         "N", "Factor 19 – Market Shortage"),
        ("Supported_Interfaces",
         "Comma-separated list (e.g. DDR4,DDR5,PCIe)",
         "Interfaces natively supported by this PN (relevant for MPU / MCU hosts). Used by the Alternative Engine to validate compatibility of candidate replacements.",
         "N", "Factor 19 – Market Shortage / Alternative Engine"),
        ("Buffer_Stock_Units",
         "Integer",
         "Safety stock units. Auto-populated from Client_Data after BOM upload.",
         "Auto", "Factor 4 – Buffer Stock"),
        ("Run_Rate_Per_Week",
         "Integer (PCB/week)",
         "Weekly PCB production rate. Auto-populated from the BOM header row.",
         "Auto", "Factor 4 – Buffer Stock"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 2 · Client_Data
    # ══════════════════════════════════════════════════════════════════════
    section("2 · Client_Data — Per-client quantity and buffer overrides", [
        ("Part_Number",
         "Text (FK → Part_Numbers)",
         "References the Part_Numbers table. Part of composite PK.",
         "Y", "Join key"),
        ("Client_ID",
         "Text (FK → Clients)",
         "References the Clients table. Part of composite PK.",
         "Y", "Join key"),
        ("Quantity_In_BOM",
         "Integer",
         "Number of units of this PN per PCB assembly for this client.",
         "Y", "Factor 4 – Buffer Stock (coverage weeks)"),
        ("Buffer_Stock_Units",
         "Integer",
         "Dedicated safety stock units held by / for this client.",
         "Y", "Factor 4 – Buffer Stock"),
        ("Custom_Lead_Time_Weeks",
         "Integer",
         "Client-negotiated lead time override. If set, replaces global Lead_Time_Weeks from Part_Numbers.",
         "N", "Factor 3 – Lead Time"),
        ("Last_Updated",
         "ISO date (YYYY-MM-DD)",
         "Timestamp of the last BOM upload or manual edit.",
         "Auto", "Audit only"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 3 · Clients
    # ══════════════════════════════════════════════════════════════════════
    section("3 · Clients — Customer master data", [
        ("Client_ID",
         "Text (unique PK)",
         "Primary key. Short identifier (e.g. CLIENT_001).",
         "Y", "Join key"),
        ("Client_Name",
         "Text",
         "Full company name of the customer.",
         "Y", "Display only"),
        ("Industry",
         "Automotive | Industrial | Consumer | Medical | Defense | Telecom | Other",
         "Industry vertical. Informs default certification re-qualification time assumptions.",
         "N", "Factor 6 – Certification"),
        ("Default_Run_Rate",
         "Integer (PCB/week)",
         "Default weekly PCB production rate when no BOM header run-rate is provided.",
         "N", "Factor 4 – Buffer Stock"),
        ("Contact_Email",
         "Text (email)",
         "Primary contact for supply chain alerts.",
         "N", "Notification only"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 4 · Tier2_Suppliers
    # ══════════════════════════════════════════════════════════════════════
    section("4 · Tier2_Suppliers — Upstream (Tier-2/3) suppliers of critical raw materials", [
        ("Supplier_ID",
         "Text (unique PK)",
         "Primary key for the Tier-2 supplier.",
         "Y", "Join key"),
        ("Supplier_Name",
         "Text",
         "Company name of the Tier-2/3 supplier.",
         "Y", "Display only"),
        ("Material",
         "Neon Gas | Photoresists | Silicon Wafers | Rare Earth Elements | Palladium Wire | SiC Substrates | CMP Slurry | GaN Substrates | other",
         "Critical material supplied. Used to map risk from raw-material shortages to Tier-1 components.",
         "Y", "Factor 14 – Tier-2 Visibility"),
        ("Country",
         "ISO country name",
         "Country of production. High concentration in one country increases Tier-2 risk score.",
         "Y", "Factor 14 – Tier-2 Visibility"),
        ("Market_Share_Pct",
         "Float (0–100 %)",
         "Estimated global market share of this supplier for the given material.",
         "N", "Factor 14 – Tier-2 Visibility"),
        ("Criticality",
         "CRITICAL | HIGH | MEDIUM | LOW",
         "Strategic criticality rating. CRITICAL = hard to substitute within 12 months.",
         "Y", "Factor 14 – Tier-2 Visibility"),
        ("Notes",
         "Text",
         "Free-text notes (e.g. war risk, export restrictions, single-plant dependency).",
         "N", "Display only"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 5 · Component_Materials
    # ══════════════════════════════════════════════════════════════════════
    section("5 · Component_Materials — Mapping: component <-> Tier-2 raw material", [
        ("Part_Number",
         "Text (FK → Part_Numbers)",
         "References the component.",
         "Y", "Join key"),
        ("Supplier_ID",
         "Text (FK → Tier2_Suppliers)",
         "References the Tier-2 supplier.",
         "Y", "Join key"),
        ("Usage_Notes",
         "Text",
         "How the material is used in this component (e.g. wafer substrate, bonding wire).",
         "N", "Display only"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 6 · EMS_Providers
    # ══════════════════════════════════════════════════════════════════════
    section("6 · EMS_Providers — Contract manufacturers (EMS / ODM)", [
        ("EMS_ID",
         "Text (unique PK)",
         "Primary key for the EMS provider.",
         "Y", "Join key"),
        ("EMS_Name",
         "Text",
         "Full company name (e.g. Foxconn, Flex, Jabil, Celestica).",
         "Y", "Factor 16 – EMS Risk"),
        ("Country",
         "ISO country name",
         "Main production country. Country-level risk feeds into EMS score.",
         "Y", "Factor 16 – EMS Risk"),
        ("Capacity_Utilization_Pct",
         "Float (0–100 %)",
         "Current line utilization. > 90 % = overloaded, increasing delivery risk.",
         "N", "Factor 16 – EMS Risk"),
        ("Financial_Health",
         "A | B | C | D",
         "Financial stability rating of the EMS provider.",
         "N", "Factor 16 – EMS Risk"),
        ("Certifications",
         "Comma-separated (ISO9001, IATF16949, AS9100, ISO13485)",
         "Quality certifications held by the EMS provider.",
         "N", "Factor 16 – EMS Risk"),
        ("Lead_Time_Weeks",
         "Integer",
         "Assembly lead time added by this EMS provider.",
         "N", "Factor 16 – EMS Risk"),
        ("Single_Client_Pct",
         "Float (0–100 %)",
         "Percentage of revenue from a single client (concentration risk for OEM).",
         "N", "Factor 16 – EMS Risk"),
        ("Notes",
         "Text",
         "Operational notes or risk flags.",
         "N", "Display only"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 7 · Distributors
    # ══════════════════════════════════════════════════════════════════════
    section("7 · Distributors — Authorized distributors", [
        ("Distributor_ID",
         "Text (unique PK)",
         "Primary key for the distributor.",
         "Y", "Join key"),
        ("Distributor_Name",
         "Text",
         "Company name (e.g. Avnet, Arrow, Digi-Key, Mouser, Future Electronics).",
         "Y", "Factor 17 – Distributor Risk"),
        ("Country",
         "ISO country name",
         "Primary country of operations.",
         "Y", "Factor 17 – Distributor Risk"),
        ("Authorized",
         "Y | N",
         "Y = authorized (franchised) distributor for this manufacturer; N = broker / independent.",
         "Y", "Factor 17 – Distributor Risk"),
        ("Stock_Level",
         "High | Medium | Low | Zero",
         "Current stock availability level at this distributor.",
         "N", "Factor 17 – Distributor Risk / Stock-Out Simulator"),
        ("Lead_Time_Weeks",
         "Integer",
         "Distribution lead time from this distributor to the OEM.",
         "N", "Factor 17 – Distributor Risk"),
        ("Financial_Health",
         "A | B | C | D",
         "Financial rating of the distributor.",
         "N", "Factor 17 – Distributor Risk"),
        ("Notes",
         "Text",
         "Free-text notes.",
         "N", "Display only"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 8 · Part_Distributors
    # ══════════════════════════════════════════════════════════════════════
    section("8 · Part_Distributors — Mapping: component <-> distributor", [
        ("Part_Number",
         "Text (FK → Part_Numbers)",
         "References the component.",
         "Y", "Join key"),
        ("Distributor_ID",
         "Text (FK → Distributors)",
         "References the distributor.",
         "Y", "Join key"),
        ("Stock_Units",
         "Integer",
         "Units currently in stock at this distributor for this PN.",
         "N", "Factor 17 – Distributor Risk / Stock-Out Simulator"),
        ("Price_USD",
         "Float",
         "Unit price in USD at this distributor. Used in switching cost calculation.",
         "N", "Switching cost calculation"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 9 · Alt_Sources
    # ══════════════════════════════════════════════════════════════════════
    section("9 · Alt_Sources — Alternative / second-source components", [
        ("Part_Number",
         "Text (FK → Part_Numbers)",
         "The original PN this alternative replaces.",
         "Y", "Factor 9 – Alternative Sources"),
        ("Supplier_Name",
         "Text",
         "Name of the supplier offering the alternative (e.g. Samsung, SK Hynix, Micron).",
         "Y", "Alternative Engine"),
        ("Interface_Type",
         "DDR3 | DDR4 | DDR5 | LPDDR4 | LPDDR4X | LPDDR5 | NOR_Flash | NAND_Flash | SPI_Flash | QSPI_Flash | SRAM | PSRAM | HyperRAM | other",
         "Memory / bus interface of this alternative. Matched against Supported_Interfaces of the host processor to compute interface compatibility score.",
         "N", "Alternative Engine – interface score (40 %)"),
        ("Package_Compatible",
         "Y | N | Partial",
         "Y = same footprint drop-in; Partial = minor PCB rework required; N = incompatible footprint.",
         "N", "Alternative Engine – package score (20 %)"),
        ("OS_Compatible",
         "Linux | RTOS | Baremetal | Any | N/A",
         "Software / OS compatibility of the alternative component.",
         "N", "Alternative Engine – notes"),
        ("Drop_In_Replacement",
         "Y | N | Partial",
         "Overall drop-in assessment combining electrical + mechanical + software compatibility.",
         "N", "Alternative Engine – display"),
        ("Porting_Effort_Hours",
         "Integer (hours)",
         "Estimated engineering hours to port / qualify this alternative. 0 = zero effort; 500+ = maximum effort (normalized internally).",
         "N", "Alternative Engine – porting score (10 %)"),
        ("Availability_Status",
         "Available | Tight | Shortage | Critical | EOL",
         "Current market availability of this specific alternative source.",
         "N", "Alternative Engine – availability score (30 %)"),
        ("Frontend_Country",
         "ISO country name",
         "Wafer fab country of the alternative supplier. Used by Factor 18 to detect hidden SPOF (geographic convergence).",
         "N", "Factor 18 – Hidden SPOF"),
        ("Backend_Country",
         "ISO country name",
         "Assembly / test country of the alternative supplier.",
         "N", "Factor 18 – Hidden SPOF"),
        ("Lead_Time_Weeks",
         "Integer",
         "Lead time of this alternative source.",
         "N", "Alternative Engine – display"),
        ("Financial_Health",
         "A | B | C | D",
         "Financial health of the alternative supplier.",
         "N", "Factor 10 – Financial Health"),
        ("Qualification_Status",
         "Qualified | In Qualification | Not Qualified | N/A",
         "Current qualification status of this alternative at the OEM / customer.",
         "N", "Factor 9 – Alternative Sources"),
        ("Allocation_Pct",
         "Float (0–100 %)",
         "Percentage of normal supply currently allocated (100 % = fully available; < 100 % = constrained).",
         "N", "Factor 11 – Allocation"),
        ("Notes",
         "Text",
         "Free-text notes, datasheet links, or migration guidance.",
         "N", "Display only"),
        ("Created_at",
         "ISO date (YYYY-MM-DD)",
         "Record creation date.",
         "Auto", "Audit only"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 10 · Supplier_Profiles
    # ══════════════════════════════════════════════════════════════════════
    section("10 · Supplier_Profiles — Detailed supplier financial and operational profiles", [
        ("Supplier_Name",
         "Text (unique)",
         "Supplier name. Must match the Manufacturer field in Part_Numbers for joins.",
         "Y", "Factor 10 – Financial Health"),
        ("Revenue_BUSD",
         "Float (USD billions)",
         "Annual revenue in USD billions.",
         "N", "Factor 10 – Financial Health"),
        ("Financial_Rating",
         "A | B | C | D",
         "Overall financial rating. D = distressed (+8 pt); C = weak (+5 pt); B = fair (+2 pt); A = strong (0 pt).",
         "Y", "Factor 10 – Financial Health"),
        ("Fab_Count",
         "Integer",
         "Total number of wafer fabs operated by this supplier globally.",
         "N", "Factor 2 – Single Source"),
        ("R_D_Pct_Revenue",
         "Float (%)",
         "R&D spend as percentage of revenue. Low R&D may signal roadmap risk.",
         "N", "Display only"),
        ("ESG_Score",
         "Float (0–100)",
         "Environmental / Social / Governance composite score.",
         "N", "Display only"),
        ("Notes",
         "Text (JSON allowed)",
         "Extended notes or JSON key-value pairs (e.g. {CEO: name, IPO: 2024}).",
         "N", "Display only"),
        ("Updated_at",
         "ISO date (YYYY-MM-DD)",
         "Date of last profile update.",
         "Auto", "Audit only"),
    ])

    # ══════════════════════════════════════════════════════════════════════
    # 11 · Market_Shortage
    # ══════════════════════════════════════════════════════════════════════
    section("11 · Market_Shortage — Global interface / technology shortage tracker", [
        ("Interface_Type",
         "DDR3 | DDR4 | DDR5 | LPDDR4 | LPDDR4X | LPDDR5 | NOR_Flash | NAND_Flash | SPI_Flash | QSPI_Flash | SRAM | PSRAM | HyperRAM | other",
         "Interface or memory technology affected by the shortage. Matched against Supported_Interfaces of each PN in the BOM.",
         "Y", "Factor 19 – Market Shortage"),
        ("Severity",
         "Available | Tight | Shortage | Critical",
         "Current shortage level. Tight = +2 pt; Shortage = +5 pt; Critical = +8 pt (added to base risk score).",
         "Y", "Factor 19 – Market Shortage"),
        ("Since_Date",
         "ISO date (YYYY-MM-DD)",
         "Start date of the shortage event.",
         "N", "Display / trend analysis"),
        ("Notes",
         "Text",
         "Context for the shortage (e.g. AI / Data-Center demand surge driven by Nvidia GPU production ramp).",
         "N", "Display only"),
        ("Source",
         "Text (e.g. Nexar API | Manual | Bloomberg | IHS Markit)",
         "Data provenance — where this shortage information was sourced.",
         "N", "Audit / credibility"),
        ("Updated_at",
         "ISO date (YYYY-MM-DD)",
         "Date of last update to this record.",
         "Auto", "Audit only"),
    ])

    # ── Legend ─────────────────────────────────────────────────────────────
    ROW += 2
    _merge(ws, ROW, 1, 5,
           "Legend:  Yellow = Required (Y) — risk score may be wrong if empty.   "
           "Green = Auto-computed by the application.   "
           "Gray = Optional — improves accuracy but not mandatory.",
           font_normal, fill_header, align_wrap)
    ws.row_dimensions[ROW].height = 28

    ws.freeze_panes = "A4"
    return ROW


if __name__ == "__main__":
    print(f"Opening {DB_PATH} ...")
    wb = openpyxl.load_workbook(str(DB_PATH))
    total_rows = build_readme(wb)
    wb.save(str(DB_PATH))
    print(f"README sheet created — {total_rows} rows written. File saved.")
