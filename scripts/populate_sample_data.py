"""
populate_sample_data.py
=======================
Popola i 7 fogli vuoti di part_numbers_db.xlsx con dati realistici
che rappresentano la complessità della supply chain elettronica.

Scenari rappresentati:
- EMS: Foxconn/BYD ad alta capacità (rischio Cina), Jabil/Flex diversificati
- Distributori: dipendenza concentrata su Arrow per componenti critici
- Hidden Single Source: alt-source "diversificate" ma tutte con fab Taiwan (TSMC)
- Tier-2: fotoresist 90% Giappone, neon 75% Ucraina, palladio 42% Russia
- Supplier Profiles: fab TSMC, Samsung, ST, NXP con materiali specifici

Uso: python populate_sample_data.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, date

DB_PATH = str(Path(__file__).parent.parent / 'data' / 'part_numbers_db.xlsx')
NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
TODAY = date.today().strftime('%Y-%m-%d')


# =============================================================================
# 1. EMS_PROVIDERS
# =============================================================================

ems_providers = pd.DataFrame([
    # EMS grandi globali con geopolitica critica
    {
        'EMS_ID': 'EMS001',
        'EMS_Name': 'Foxconn Technology Group',
        'Country': 'China',
        'Financial_Health': 'B',
        'Capacity_Utilization_Pct': 92,
        'Certifications': 'ISO9001,IATF16949,IPC-J-STD-001',
        'Backup_Sites_Count': 3,
        'Years_Business': 50,
        'Notes': 'Principale sito Zhengzhou. Alta dipendenza da politica export Cina. Cliente Apple/NXP/TI. Rischio geopolitico elevato.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'EMS_ID': 'EMS002',
        'EMS_Name': 'BYD Electronics',
        'Country': 'China',
        'Financial_Health': 'B',
        'Capacity_Utilization_Pct': 95,
        'Certifications': 'ISO9001,IATF16949',
        'Backup_Sites_Count': 2,
        'Years_Business': 28,
        'Notes': 'Capacità quasi satura. Gruppo BYD in espansione EV riduce slot per electronics. Rischio priorità interna.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'EMS_ID': 'EMS003',
        'EMS_Name': 'Wistron Corporation',
        'Country': 'Taiwan',
        'Financial_Health': 'B',
        'Capacity_Utilization_Pct': 88,
        'Certifications': 'ISO9001,IPC-J-STD-001,IATF16949',
        'Backup_Sites_Count': 2,
        'Years_Business': 31,
        'Notes': 'Sito principale Zhongli (Taiwan). Rischio geopolitico Taiwan Strait. Backup India in corso di espansione.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    # EMS diversificati con minor rischio
    {
        'EMS_ID': 'EMS004',
        'EMS_Name': 'Jabil Circuit Inc.',
        'Country': 'USA',
        'Financial_Health': 'A',
        'Capacity_Utilization_Pct': 78,
        'Certifications': 'ISO9001,IATF16949,AS9100,IPC-J-STD-001',
        'Backup_Sites_Count': 8,
        'Years_Business': 58,
        'Notes': '30+ siti in 25 paesi. Certificato ITAR. Cliente automotive Tier-1 (Bosch, Continental). Migliore profilo di resilienza.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'EMS_ID': 'EMS005',
        'EMS_Name': 'Flex Ltd (Flextronics)',
        'Country': 'Singapore',
        'Financial_Health': 'A',
        'Capacity_Utilization_Pct': 81,
        'Certifications': 'ISO9001,IATF16949,IPC-J-STD-001,ISO14001',
        'Backup_Sites_Count': 6,
        'Years_Business': 44,
        'Notes': 'HQ Singapore, siti in Malaysia/India/Messico/Europa. Forte in automotive e medical. Doppio fornitore raccomandato con Jabil.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'EMS_ID': 'EMS006',
        'EMS_Name': 'Celestica Inc.',
        'Country': 'Canada',
        'Financial_Health': 'B',
        'Capacity_Utilization_Pct': 74,
        'Certifications': 'ISO9001,AS9100,IPC-J-STD-001',
        'Backup_Sites_Count': 4,
        'Years_Business': 30,
        'Notes': 'Specializzato aerospace/defence e telecom. Certificato AS9100 Rev D. Capacità libera disponibile per urgenze.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'EMS_ID': 'EMS007',
        'EMS_Name': 'Sanmina Corporation',
        'Country': 'USA',
        'Financial_Health': 'A',
        'Capacity_Utilization_Pct': 70,
        'Certifications': 'ISO9001,IATF16949,AS9100,IPC-J-STD-001,ISO13485',
        'Backup_Sites_Count': 5,
        'Years_Business': 46,
        'Notes': 'Certificato Medical (ISO13485) e Automotive. Siti USA/Messico/Europa. Ottimo per prodotti safety-critical.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'EMS_ID': 'EMS008',
        'EMS_Name': 'Benchmark Electronics',
        'Country': 'USA',
        'Financial_Health': 'B',
        'Capacity_Utilization_Pct': 65,
        'Certifications': 'ISO9001,IATF16949',
        'Backup_Sites_Count': 3,
        'Years_Business': 42,
        'Notes': 'Focalizzato su volumi medi, complessi. Forte in industrial e defence. Bassa capacità utilizzata = flessibilità per picchi.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
])


# =============================================================================
# 2. DISTRIBUTORS
# =============================================================================

distributors = pd.DataFrame([
    {
        'Distributor_ID': 'DIST001',
        'Name': 'Arrow Electronics',
        'Country': 'USA',
        'Financial_Health': 'A',
        'Lead_Time_Markup_Weeks': 1,
        'Stock_Level_Weeks_Coverage': 8,
        'Certifications': 'AS9120B,ISO9001',
        'Backup_Count': 3,
        'Notes': 'Distributore #1 globale per revenue. Principale per NXP, ST, TI, Marvell, Mobileye. ALTA CONCENTRAZIONE — 14 PN dipendenti.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'Distributor_ID': 'DIST002',
        'Name': 'Avnet Inc.',
        'Country': 'USA',
        'Financial_Health': 'A',
        'Lead_Time_Markup_Weeks': 1,
        'Stock_Level_Weeks_Coverage': 6,
        'Certifications': 'AS9120B,ISO9001,ISO14001',
        'Backup_Count': 3,
        'Notes': 'Distributore #2 globale. Forte in memoria (Samsung, Micron) e analogici. Programma Avnet Silica per EMEA.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'Distributor_ID': 'DIST003',
        'Name': 'Mouser Electronics',
        'Country': 'USA',
        'Financial_Health': 'A',
        'Lead_Time_Markup_Weeks': 0,
        'Stock_Level_Weeks_Coverage': 4,
        'Certifications': 'ISO9001',
        'Backup_Count': 2,
        'Notes': 'Catalogo vastissimo (>1.2M PN). Ottimo per produzione bassa/media. No accordi di allocazione preferenziale con produttori.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'Distributor_ID': 'DIST004',
        'Name': 'DigiKey Corporation',
        'Country': 'USA',
        'Financial_Health': 'A',
        'Lead_Time_Markup_Weeks': 0,
        'Stock_Level_Weeks_Coverage': 5,
        'Certifications': 'ISO9001',
        'Backup_Count': 2,
        'Notes': 'Eccellente per prototipi e piccole serie. Singolo magazzino Minnesota (rischio resilienza). Shipping globale 24h.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'Distributor_ID': 'DIST005',
        'Name': 'TTI Inc.',
        'Country': 'USA',
        'Financial_Health': 'B',
        'Lead_Time_Markup_Weeks': 2,
        'Stock_Level_Weeks_Coverage': 12,
        'Certifications': 'AS9120B,ISO9001',
        'Backup_Count': 2,
        'Notes': 'Specializzato in passivi, connettori e sensori. Stock profondo su componenti standard. Parte del gruppo Berkshire Hathaway.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'Distributor_ID': 'DIST006',
        'Name': 'Rutronik Elektronische Bauelemente',
        'Country': 'Germany',
        'Financial_Health': 'B',
        'Lead_Time_Markup_Weeks': 2,
        'Stock_Level_Weeks_Coverage': 4,
        'Certifications': 'ISO9001,IATF16949',
        'Backup_Count': 1,
        'Notes': 'Principale distributore europeo indipendente. Forte con Infineon, Renesas, Murata in EMEA. Certificato automotive.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'Distributor_ID': 'DIST007',
        'Name': 'Future Electronics',
        'Country': 'Canada',
        'Financial_Health': 'B',
        'Lead_Time_Markup_Weeks': 2,
        'Stock_Level_Weeks_Coverage': 3,
        'Certifications': 'ISO9001',
        'Backup_Count': 1,
        'Notes': 'Forte con Qualcomm, Quectel, moduli wireless. Privato (Farnsworth). Stock più basso vs. Arrow/Avnet.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    {
        'Distributor_ID': 'DIST008',
        'Name': 'Rochester Electronics',
        'Country': 'USA',
        'Financial_Health': 'A',
        'Lead_Time_Markup_Weeks': 8,
        'Stock_Level_Weeks_Coverage': 52,
        'Certifications': 'AS9120B,ISO9001',
        'Backup_Count': 0,
        'Notes': 'Specialista EOL/legacy. Unica fonte per PN obsoleti/NRND. Stock di 15+ anni. Lead time markup alto ma disponibilità garantita.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
])


# =============================================================================
# 3. PART_DISTRIBUTORS
# =============================================================================
# Scenari di rischio:
# - EYEQ5H: mono-distributore Arrow (componente proprietario Mobileye)
# - QCA6174A-5: solo Future Electronics (accordo preferenziale Qualcomm)
# - S32K344: Arrow primario con backup Avnet (rischio concentrazione NXP)
# - 88Q2112: solo Arrow (accordo esclusivo Marvell)
# - EC25-E: Mouser+Future, nessun grande distributore autorizzato

part_distributors = pd.DataFrame([
    # --- MCU NXP MKE02Z64VLD4 ---
    {'Part_Number': 'MKE02Z64VLD4', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 60, 'Created_at': NOW},
    {'Part_Number': 'MKE02Z64VLD4', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 30, 'Created_at': NOW},
    {'Part_Number': 'MKE02Z64VLD4', 'Distributor_ID': 'DIST003', 'Priority': 'Secondary', 'Allocation_Pct': 10, 'Created_at': NOW},

    # --- MPU ST STM32MP157CAC3 ---
    {'Part_Number': 'STM32MP157CAC3', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 70, 'Created_at': NOW},
    {'Part_Number': 'STM32MP157CAC3', 'Distributor_ID': 'DIST006', 'Priority': 'Secondary', 'Allocation_Pct': 30, 'Created_at': NOW},

    # --- PMIC ST STPMIC1APQR ---
    {'Part_Number': 'STPMIC1APQR', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 55, 'Created_at': NOW},
    {'Part_Number': 'STPMIC1APQR', 'Distributor_ID': 'DIST006', 'Priority': 'Secondary', 'Allocation_Pct': 45, 'Created_at': NOW},

    # --- Sensor Bosch BME280 ---
    {'Part_Number': 'BME280', 'Distributor_ID': 'DIST002', 'Priority': 'Primary', 'Allocation_Pct': 50, 'Created_at': NOW},
    {'Part_Number': 'BME280', 'Distributor_ID': 'DIST003', 'Priority': 'Secondary', 'Allocation_Pct': 30, 'Created_at': NOW},
    {'Part_Number': 'BME280', 'Distributor_ID': 'DIST004', 'Priority': 'Secondary', 'Allocation_Pct': 20, 'Created_at': NOW},

    # --- WiFi Espressif ESP32-WROOM-32E ---
    {'Part_Number': 'ESP32-WROOM-32E', 'Distributor_ID': 'DIST003', 'Priority': 'Primary', 'Allocation_Pct': 55, 'Created_at': NOW},
    {'Part_Number': 'ESP32-WROOM-32E', 'Distributor_ID': 'DIST007', 'Priority': 'Secondary', 'Allocation_Pct': 45, 'Created_at': NOW},

    # --- MLCC Murata GRM155R71C104KA88D ---
    {'Part_Number': 'GRM155R71C104KA88D', 'Distributor_ID': 'DIST005', 'Priority': 'Primary', 'Allocation_Pct': 50, 'Created_at': NOW},
    {'Part_Number': 'GRM155R71C104KA88D', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 30, 'Created_at': NOW},
    {'Part_Number': 'GRM155R71C104KA88D', 'Distributor_ID': 'DIST004', 'Priority': 'Secondary', 'Allocation_Pct': 20, 'Created_at': NOW},

    # --- Buck TI TPS62840DLCR ---
    {'Part_Number': 'TPS62840DLCR', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 65, 'Created_at': NOW},
    {'Part_Number': 'TPS62840DLCR', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 35, 'Created_at': NOW},

    # --- LPDDR4 Samsung K4B4G1646E-BYMA ---
    {'Part_Number': 'K4B4G1646E-BYMA', 'Distributor_ID': 'DIST002', 'Priority': 'Primary', 'Allocation_Pct': 80, 'Created_at': NOW},
    {'Part_Number': 'K4B4G1646E-BYMA', 'Distributor_ID': 'DIST001', 'Priority': 'Secondary', 'Allocation_Pct': 20, 'Created_at': NOW},

    # --- CAN Infineon TLE9251VLE ---
    {'Part_Number': 'TLE9251VLE', 'Distributor_ID': 'DIST006', 'Priority': 'Primary', 'Allocation_Pct': 60, 'Created_at': NOW},
    {'Part_Number': 'TLE9251VLE', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 40, 'Created_at': NOW},

    # --- MCU NXP S32K344 (ADAS critical) ---
    {'Part_Number': 'S32K344', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 85, 'Created_at': NOW},
    {'Part_Number': 'S32K344', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 15, 'Created_at': NOW},

    # --- MPU NXP S32G274A (ADAS) ---
    {'Part_Number': 'S32G274A', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 90, 'Created_at': NOW},
    {'Part_Number': 'S32G274A', 'Distributor_ID': 'DIST006', 'Priority': 'Secondary', 'Allocation_Pct': 10, 'Created_at': NOW},

    # --- PMIC NXP PF5024 ---
    {'Part_Number': 'PF5024', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 75, 'Created_at': NOW},
    {'Part_Number': 'PF5024', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 25, 'Created_at': NOW},

    # --- !! EYEQ5H Mobileye: MONO-DISTRIBUTORE Arrow !! ---
    # Componente proprietario Mobileye/Intel: unico canale ufficiale Arrow
    {'Part_Number': 'EYEQ5H', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 100, 'Created_at': NOW},

    # --- LPDDR4X Micron MT53E256M32D1DS ---
    {'Part_Number': 'MT53E256M32D1DS-046', 'Distributor_ID': 'DIST002', 'Priority': 'Primary', 'Allocation_Pct': 70, 'Created_at': NOW},
    {'Part_Number': 'MT53E256M32D1DS-046', 'Distributor_ID': 'DIST001', 'Priority': 'Secondary', 'Allocation_Pct': 30, 'Created_at': NOW},

    # --- NOR Flash Macronix MX25U25645G ---
    {'Part_Number': 'MX25U25645G', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 55, 'Created_at': NOW},
    {'Part_Number': 'MX25U25645G', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 45, 'Created_at': NOW},

    # --- !! 88Q2112 Marvell 100BASE-T1: solo Arrow (accordo esclusivo) !! ---
    {'Part_Number': '88Q2112-A2-NNP2I000', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 100, 'Created_at': NOW},

    # --- PMIC TI TPS65263 ---
    {'Part_Number': 'TPS65263-1QRGZRQ1', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 60, 'Created_at': NOW},
    {'Part_Number': 'TPS65263-1QRGZRQ1', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 40, 'Created_at': NOW},

    # --- IMU Bosch SMI230 ---
    {'Part_Number': 'SMI230', 'Distributor_ID': 'DIST002', 'Priority': 'Primary', 'Allocation_Pct': 55, 'Created_at': NOW},
    {'Part_Number': 'SMI230', 'Distributor_ID': 'DIST006', 'Priority': 'Secondary', 'Allocation_Pct': 45, 'Created_at': NOW},

    # --- CAN NXP TJA1463 ---
    {'Part_Number': 'TJA1463', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 70, 'Created_at': NOW},
    {'Part_Number': 'TJA1463', 'Distributor_ID': 'DIST006', 'Priority': 'Secondary', 'Allocation_Pct': 30, 'Created_at': NOW},

    # --- !! QCA6174A-5 Qualcomm WiFi: solo Future Electronics !! ---
    {'Part_Number': 'QCA6174A-5', 'Distributor_ID': 'DIST007', 'Priority': 'Primary', 'Allocation_Pct': 100, 'Created_at': NOW},

    # --- !! EC25-E Quectel LTE: Mouser+Future, nessun grande dist. !! ---
    {'Part_Number': 'EC25-E', 'Distributor_ID': 'DIST003', 'Priority': 'Primary', 'Allocation_Pct': 60, 'Created_at': NOW},
    {'Part_Number': 'EC25-E', 'Distributor_ID': 'DIST007', 'Priority': 'Secondary', 'Allocation_Pct': 40, 'Created_at': NOW},

    # --- NAND Micron MT29F4G08 ---
    {'Part_Number': 'MT29F4G08ABAFAWP', 'Distributor_ID': 'DIST002', 'Priority': 'Primary', 'Allocation_Pct': 65, 'Created_at': NOW},
    {'Part_Number': 'MT29F4G08ABAFAWP', 'Distributor_ID': 'DIST001', 'Priority': 'Secondary', 'Allocation_Pct': 35, 'Created_at': NOW},

    # --- DDR3 Alliance AS4C256M16D3C ---
    {'Part_Number': 'AS4C256M16D3C-12', 'Distributor_ID': 'DIST002', 'Priority': 'Primary', 'Allocation_Pct': 60, 'Created_at': NOW},
    {'Part_Number': 'AS4C256M16D3C-12', 'Distributor_ID': 'DIST008', 'Priority': 'Secondary', 'Allocation_Pct': 40, 'Created_at': NOW},

    # --- Ethernet Microchip LAN9250 ---
    {'Part_Number': 'LAN9250', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 55, 'Created_at': NOW},
    {'Part_Number': 'LAN9250', 'Distributor_ID': 'DIST003', 'Priority': 'Secondary', 'Allocation_Pct': 45, 'Created_at': NOW},

    # --- Humidity Sensor Silicon Labs SI7021 ---
    {'Part_Number': 'SI7021-A20-GM1R', 'Distributor_ID': 'DIST003', 'Priority': 'Primary', 'Allocation_Pct': 50, 'Created_at': NOW},
    {'Part_Number': 'SI7021-A20-GM1R', 'Distributor_ID': 'DIST004', 'Priority': 'Secondary', 'Allocation_Pct': 50, 'Created_at': NOW},

    # --- Passivi (TTI specialista passivi) ---
    {'Part_Number': 'GCM32ER71E106KA37', 'Distributor_ID': 'DIST005', 'Priority': 'Primary', 'Allocation_Pct': 60, 'Created_at': NOW},
    {'Part_Number': 'GCM32ER71E106KA37', 'Distributor_ID': 'DIST003', 'Priority': 'Secondary', 'Allocation_Pct': 40, 'Created_at': NOW},

    {'Part_Number': 'PESD2CAN-U', 'Distributor_ID': 'DIST006', 'Priority': 'Primary', 'Allocation_Pct': 65, 'Created_at': NOW},
    {'Part_Number': 'PESD2CAN-U', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 35, 'Created_at': NOW},

    {'Part_Number': 'VLS252015HBX-1R0M', 'Distributor_ID': 'DIST005', 'Priority': 'Primary', 'Allocation_Pct': 55, 'Created_at': NOW},
    {'Part_Number': 'VLS252015HBX-1R0M', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 45, 'Created_at': NOW},

    {'Part_Number': 'C2012X7R1H104K', 'Distributor_ID': 'DIST005', 'Priority': 'Primary', 'Allocation_Pct': 50, 'Created_at': NOW},
    {'Part_Number': 'C2012X7R1H104K', 'Distributor_ID': 'DIST004', 'Priority': 'Secondary', 'Allocation_Pct': 50, 'Created_at': NOW},

    {'Part_Number': '744043100', 'Distributor_ID': 'DIST006', 'Priority': 'Primary', 'Allocation_Pct': 60, 'Created_at': NOW},
    {'Part_Number': '744043100', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 40, 'Created_at': NOW},

    {'Part_Number': 'IHLP2525CZER1R0M11', 'Distributor_ID': 'DIST005', 'Priority': 'Primary', 'Allocation_Pct': 70, 'Created_at': NOW},
    {'Part_Number': 'IHLP2525CZER1R0M11', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 30, 'Created_at': NOW},

    # --- Connettori (TTI/Avnet specialisti) ---
    {'Part_Number': '1-84953-4', 'Distributor_ID': 'DIST005', 'Priority': 'Primary', 'Allocation_Pct': 55, 'Created_at': NOW},
    {'Part_Number': '1-84953-4', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 45, 'Created_at': NOW},

    {'Part_Number': '5025781070', 'Distributor_ID': 'DIST005', 'Priority': 'Primary', 'Allocation_Pct': 60, 'Created_at': NOW},
    {'Part_Number': '5025781070', 'Distributor_ID': 'DIST003', 'Priority': 'Secondary', 'Allocation_Pct': 40, 'Created_at': NOW},

    {'Part_Number': '1-2141530-1-AUT', 'Distributor_ID': 'DIST002', 'Priority': 'Primary', 'Allocation_Pct': 55, 'Created_at': NOW},
    {'Part_Number': '1-2141530-1-AUT', 'Distributor_ID': 'DIST001', 'Priority': 'Secondary', 'Allocation_Pct': 45, 'Created_at': NOW},

    {'Part_Number': '10118194-0001LF', 'Distributor_ID': 'DIST005', 'Priority': 'Primary', 'Allocation_Pct': 65, 'Created_at': NOW},
    {'Part_Number': '10118194-0001LF', 'Distributor_ID': 'DIST002', 'Priority': 'Secondary', 'Allocation_Pct': 35, 'Created_at': NOW},

    # --- MPU Renesas R9A07G044L23GBG ---
    {'Part_Number': 'R9A07G044L23GBG', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 55, 'Created_at': NOW},
    {'Part_Number': 'R9A07G044L23GBG', 'Distributor_ID': 'DIST006', 'Priority': 'Secondary', 'Allocation_Pct': 45, 'Created_at': NOW},

    # --- PMIC Renesas RAA215300 ---
    {'Part_Number': 'RAA215300', 'Distributor_ID': 'DIST001', 'Priority': 'Primary', 'Allocation_Pct': 60, 'Created_at': NOW},
    {'Part_Number': 'RAA215300', 'Distributor_ID': 'DIST006', 'Priority': 'Secondary', 'Allocation_Pct': 40, 'Created_at': NOW},
])


# =============================================================================
# 4. ALT_SOURCES
# =============================================================================
# Scenari hidden SPOF:
# - STM32MP157 alt: NXP i.MX8 → anche lui Taiwan (TSMC) = hidden SPOF
# - EYEQ5H alt: NVIDIA Orin → fab TSMC Taiwan = hidden SPOF
# - MX25U25645G alt: Winbond → anche Taiwan = hidden SPOF
# - 88Q2112 alt: Broadcom → anche Taiwan (TSMC) = hidden SPOF
# - QCA6174A-5 alt: Intel AX200 → anche Taiwan (TSMC) = hidden SPOF

alt_sources = pd.DataFrame([
    # --- MCU NXP S32K344: alt Renesas RL78 (Giappone) - DIVERSIFICATO OK ---
    {
        'Part_Number': 'S32K344',
        'Supplier_Name': 'Renesas Electronics',
        'Frontend_Country': 'Japan',
        'Backend_Country': 'Malaysia',
        'Lead_Time_Weeks': 16,
        'Financial_Health': 'A',
        'Qualification_Status': 'Qualified',
        'Allocation_Pct': 0,
        'Notes': 'Alt: RH850/U2A. Fab Naka (Giappone). Riqualifica AEC-Q100 completata. Diversificazione geografica reale.',
        'Created_at': NOW,
    },
    # --- MPU STM32MP157: alt NXP i.MX8M → HIDDEN SPOF (entrambi TSMC Taiwan) ---
    {
        'Part_Number': 'STM32MP157CAC3',
        'Supplier_Name': 'NXP Semiconductors',
        'Frontend_Country': 'Taiwan',  # ← TSMC, stesso di ST per certi nodi!
        'Backend_Country': 'Malaysia',
        'Lead_Time_Weeks': 20,
        'Financial_Health': 'A',
        'Qualification_Status': 'In_Progress',
        'Allocation_Pct': 0,
        'Notes': 'Alt: i.MX8M Plus. ATTENZIONE: ST usa fab propria Crolles ma alt usa TSMC Taiwan. Qualifica SW in corso (18 mesi stimati).',
        'Created_at': NOW,
    },
    # --- EYEQ5H Mobileye: alt NVIDIA Orin → HIDDEN SPOF (TSMC Taiwan) ---
    {
        'Part_Number': 'EYEQ5H',
        'Supplier_Name': 'NVIDIA Corporation',
        'Frontend_Country': 'Taiwan',  # ← TSMC N7/N5
        'Backend_Country': 'South Korea',
        'Lead_Time_Weeks': 52,
        'Financial_Health': 'A',
        'Qualification_Status': 'Not_Started',
        'Allocation_Pct': 0,
        'Notes': 'Alt: Orin AGX NX. Fab TSMC N7 Taiwan. HIDDEN SPOF: entrambi dipendenti da TSMC. Riqualifica ADAS richiede 24+ mesi.',
        'Created_at': NOW,
    },
    # --- LPDDR4X Micron: alt Samsung → DIVERSIFICATO (fab Korea) ---
    {
        'Part_Number': 'MT53E256M32D1DS-046',
        'Supplier_Name': 'Samsung Semiconductor',
        'Frontend_Country': 'South Korea',
        'Backend_Country': 'South Korea',
        'Lead_Time_Weeks': 14,
        'Financial_Health': 'A',
        'Qualification_Status': 'Qualified',
        'Allocation_Pct': 30,
        'Notes': 'Alt: K4F8E304HB-MGCJ. Fab Pyeongtaek (Korea). Diversificazione reale. 30% acquisti già su Samsung.',
        'Created_at': NOW,
    },
    # --- NOR Flash Macronix: alt Winbond → HIDDEN SPOF (entrambi Taiwan) ---
    {
        'Part_Number': 'MX25U25645G',
        'Supplier_Name': 'Winbond Electronics',
        'Frontend_Country': 'Taiwan',  # ← Fab Taichung
        'Backend_Country': 'Taiwan',
        'Lead_Time_Weeks': 12,
        'Financial_Health': 'B',
        'Qualification_Status': 'Qualified',
        'Allocation_Pct': 20,
        'Notes': 'Alt: W25Q256JV. HIDDEN SPOF: Macronix fab Hsinchu + Winbond fab Taichung = entrambi Taiwan. Blocco geopolitico colpisce tutti.',
        'Created_at': NOW,
    },
    # --- Marvell 100BASE-T1: alt Broadcom → HIDDEN SPOF (TSMC Taiwan) ---
    {
        'Part_Number': '88Q2112-A2-NNP2I000',
        'Supplier_Name': 'Broadcom Inc.',
        'Frontend_Country': 'Taiwan',  # ← TSMC
        'Backend_Country': 'Malaysia',
        'Lead_Time_Weeks': 24,
        'Financial_Health': 'A',
        'Qualification_Status': 'In_Progress',
        'Allocation_Pct': 0,
        'Notes': 'Alt: BCM54210PE (non automotive-grade). HIDDEN SPOF: sia Marvell che Broadcom fabless su TSMC Taiwan. Qualifica OPEN-Q in corso.',
        'Created_at': NOW,
    },
    # --- Qualcomm QCA6174: alt Intel AX200 → HIDDEN SPOF (TSMC Taiwan) ---
    {
        'Part_Number': 'QCA6174A-5',
        'Supplier_Name': 'Intel Corporation',
        'Frontend_Country': 'Taiwan',  # ← TSMC
        'Backend_Country': 'Malaysia',
        'Lead_Time_Weeks': 16,
        'Financial_Health': 'A',
        'Qualification_Status': 'Qualified',
        'Allocation_Pct': 0,
        'Notes': 'Alt: AX200NGW. HIDDEN SPOF: Qualcomm fabless TSMC + Intel Wi-Fi usa TSMC Taiwan. Solo apparente diversificazione.',
        'Created_at': NOW,
    },
    # --- Espressif ESP32: alt Nordic nRF5340 → DIVERSIFICATO (TSMC ma diverso paese?) ---
    {
        'Part_Number': 'ESP32-WROOM-32E',
        'Supplier_Name': 'Nordic Semiconductor',
        'Frontend_Country': 'Taiwan',  # ← TSMC
        'Backend_Country': 'Malaysia',
        'Lead_Time_Weeks': 14,
        'Financial_Health': 'B',
        'Qualification_Status': 'In_Progress',
        'Allocation_Pct': 0,
        'Notes': 'Alt: nRF5340-DK. Diverso stack (BLE only, no WiFi). HIDDEN SPOF parziale: entrambi usano TSMC. Cambio richiede redesign RF.',
        'Created_at': NOW,
    },
    # --- Renesas MPU: alt NXP i.MX8 → HIDDEN SPOF parziale ---
    {
        'Part_Number': 'R9A07G044L23GBG',
        'Supplier_Name': 'NXP Semiconductors',
        'Frontend_Country': 'Taiwan',
        'Backend_Country': 'Malaysia',
        'Lead_Time_Weeks': 20,
        'Financial_Health': 'A',
        'Qualification_Status': 'Not_Started',
        'Allocation_Pct': 0,
        'Notes': 'Alt: i.MX93. Renesas fab propria Giappone (basso rischio), alt usa TSMC Taiwan. Switch aumenta esposizione geopolitica.',
        'Created_at': NOW,
    },
    # --- NAND Micron: alt Kioxia → DIVERSIFICATO (Giappone) ---
    {
        'Part_Number': 'MT29F4G08ABAFAWP',
        'Supplier_Name': 'Kioxia Corporation',
        'Frontend_Country': 'Japan',
        'Backend_Country': 'Japan',
        'Lead_Time_Weeks': 16,
        'Financial_Health': 'B',
        'Qualification_Status': 'Qualified',
        'Allocation_Pct': 25,
        'Notes': 'Alt: TC58NVG2S0HBAI4. Fab Yokkaichi (Giappone). Buona diversificazione. Kioxia ex-Toshiba. Rating B per debito post-buyout.',
        'Created_at': NOW,
    },
    # --- Bosch BME280: alt TDK/InvenSense → DIVERSIFICATO ---
    {
        'Part_Number': 'BME280',
        'Supplier_Name': 'Measurement Specialties (TE)',
        'Frontend_Country': 'USA',
        'Backend_Country': 'China',
        'Lead_Time_Weeks': 12,
        'Financial_Health': 'A',
        'Qualification_Status': 'In_Progress',
        'Allocation_Pct': 0,
        'Notes': 'Alt: MS8607. Fab MEMS USA. Diversificazione geografica reale vs Bosch (Germania). Backend China rimane a rischio.',
        'Created_at': NOW,
    },
])


# =============================================================================
# 5. TIER2_SUPPLIERS
# =============================================================================

tier2_suppliers = pd.DataFrame([
    # --- Silicon Wafers (concentrazione Giappone ~64%) ---
    {'Tier2_Supplier_ID': 'T2-001', 'Tier2_Supplier_Name': 'Shin-Etsu Chemical', 'Material_Type': 'Silicon Wafers', 'Material_Key': 'silicon_wafers', 'Country': 'Japan', 'Market_Share_Pct': 28, 'Criticality': 'CRITICAL', 'Substitutability': 'Very Low', 'Notes': 'Leader mondiale 300mm wafer. Fab Shirakawa/Naoetsu. Cliente TSMC/Samsung/Intel. Nessun equivalente fuori Giappone per purezza richiesta.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-002', 'Tier2_Supplier_Name': 'SUMCO Corporation', 'Material_Type': 'Silicon Wafers', 'Material_Key': 'silicon_wafers', 'Country': 'Japan', 'Market_Share_Pct': 26, 'Criticality': 'CRITICAL', 'Substitutability': 'Very Low', 'Notes': 'JV ShinEtsu+Mitsubishi. Fab Imari/Yonezawa. Capacità 300mm vincolata. Lead time 18+ mesi per nuova capacità.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-003', 'Tier2_Supplier_Name': 'Siltronic AG', 'Material_Type': 'Silicon Wafers', 'Material_Key': 'silicon_wafers', 'Country': 'Germany', 'Market_Share_Pct': 13, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Fab Burghausen/Singapore. Unico grande player europeo. Quotato FWB. Acquisizione GlobalWafers bloccata UE 2022.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-004', 'Tier2_Supplier_Name': 'SK Siltron', 'Material_Type': 'Silicon Wafers', 'Material_Key': 'silicon_wafers', 'Country': 'South Korea', 'Market_Share_Pct': 11, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Controllata SK Group. Fab Gumi (Korea). Forte integrazione verticale SK Hynix. Espansione in SiC wafer.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-005', 'Tier2_Supplier_Name': 'GlobalWafers', 'Material_Type': 'Silicon Wafers', 'Material_Key': 'silicon_wafers', 'Country': 'Taiwan', 'Market_Share_Pct': 16, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Fab Taiwan/Texas/Denmark. Rischio geopolitico Taiwan. $5B investimento Texas 2024 per CHIPS Act.', 'Created_at': NOW, 'Updated_at': NOW},

    # --- Photoresists (concentrazione Giappone ~85%) ---
    {'Tier2_Supplier_ID': 'T2-006', 'Tier2_Supplier_Name': 'JSR Corporation', 'Material_Type': 'Photoresists', 'Material_Key': 'photoresists', 'Country': 'Japan', 'Market_Share_Pct': 35, 'Criticality': 'CRITICAL', 'Substitutability': 'Very Low', 'Notes': 'Leader EUV photoresist. Nazionalizzato dal governo giapponese 2023 per strategicità. Unico fornitore qualificato per TSMC N3.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-007', 'Tier2_Supplier_Name': 'Tokyo Ohka Kogyo (TOK)', 'Material_Type': 'Photoresists', 'Material_Key': 'photoresists', 'Country': 'Japan', 'Market_Share_Pct': 25, 'Criticality': 'CRITICAL', 'Substitutability': 'Very Low', 'Notes': 'Specializzato ArF/EUV. Fab Sagamihara. Esportazioni controllate METI. Qualifica nuovi photoresist richiede 2-3 anni.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-008', 'Tier2_Supplier_Name': 'Shin-Etsu Chemical (MicroSi)', 'Material_Type': 'Photoresists', 'Material_Key': 'photoresists', 'Country': 'Japan', 'Market_Share_Pct': 15, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Divisione chimica Shin-Etsu. Forte su i-line/KrF. Meno esposto EUV vs JSR/TOK.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-009', 'Tier2_Supplier_Name': 'DuPont Electronics', 'Material_Type': 'Photoresists', 'Material_Key': 'photoresists', 'Country': 'USA', 'Market_Share_Pct': 10, 'Criticality': 'MEDIUM', 'Substitutability': 'Medium', 'Notes': 'Ex-Dow Chemical. Fab Marlborough MA. Forte su packaging/advanced packaging. Non leader su EUV.', 'Created_at': NOW, 'Updated_at': NOW},

    # --- Neon Gas (concentrazione Ucraina ~75% pre-guerra) ---
    {'Tier2_Supplier_ID': 'T2-010', 'Tier2_Supplier_Name': 'Ingas', 'Material_Type': 'Neon Gas', 'Material_Key': 'neon_gas', 'Country': 'Ukraine', 'Market_Share_Pct': 45, 'Criticality': 'CRITICAL', 'Substitutability': 'Very Low', 'Notes': 'Mariupol (ora zona conflitto). Impianto distrutto 2022. Produzione dimezzata. Neon purezza 99.999% richiesta per laser ArF.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-011', 'Tier2_Supplier_Name': 'Cryoin Engineering', 'Material_Type': 'Neon Gas', 'Material_Key': 'neon_gas', 'Country': 'Ukraine', 'Market_Share_Pct': 30, 'Criticality': 'CRITICAL', 'Substitutability': 'Very Low', 'Notes': 'Odessa. Operativo ma a rischio attacchi infrastruttura. Principale alternativa a Ingas nel breve periodo.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-012', 'Tier2_Supplier_Name': 'Air Liquide', 'Material_Type': 'Neon Gas', 'Material_Key': 'neon_gas', 'Country': 'France', 'Market_Share_Pct': 10, 'Criticality': 'HIGH', 'Substitutability': 'Medium', 'Notes': 'Produzione neon da separazione aria. Costo 3-4x vs Ucraina. Espansione capacità in corso post-2022 crisis.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-013', 'Tier2_Supplier_Name': 'Linde plc', 'Material_Type': 'Neon Gas', 'Material_Key': 'neon_gas', 'Country': 'Germany', 'Market_Share_Pct': 8, 'Criticality': 'HIGH', 'Substitutability': 'Medium', 'Notes': 'Global industrial gas. Neon prodotto in USA/Australia come sottoprodotto acciaio. Volume limitato.', 'Created_at': NOW, 'Updated_at': NOW},

    # --- Rare Earth Elements (concentrazione Cina ~70%) ---
    {'Tier2_Supplier_ID': 'T2-014', 'Tier2_Supplier_Name': 'China Northern Rare Earth Group', 'Material_Type': 'Rare Earth Elements', 'Material_Key': 'rare_earth', 'Country': 'China', 'Market_Share_Pct': 40, 'Criticality': 'CRITICAL', 'Substitutability': 'Very Low', 'Notes': 'Più grande produttore mondiale REE. Controllato stato cinese. Export quota settembre 2023 ridotte 25%. Rischio sanzioni/export ban.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-015', 'Tier2_Supplier_Name': 'China Minmetals Rare Earth', 'Material_Type': 'Rare Earth Elements', 'Material_Key': 'rare_earth', 'Country': 'China', 'Market_Share_Pct': 20, 'Criticality': 'CRITICAL', 'Substitutability': 'Very Low', 'Notes': 'Heavy REE (disprosio, terbio). Essenziali per magneti permanenti in sensori/attuatori. Controllo governativo.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-016', 'Tier2_Supplier_Name': 'MP Materials Corp.', 'Material_Type': 'Rare Earth Elements', 'Material_Key': 'rare_earth', 'Country': 'USA', 'Market_Share_Pct': 15, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Mountain Pass CA. Unica miniera REE operativa USA. DOD contract $35M. Solo light REE (no heavy REE per magneti).', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-017', 'Tier2_Supplier_Name': 'Lynas Rare Earths', 'Material_Type': 'Rare Earth Elements', 'Material_Key': 'rare_earth', 'Country': 'Australia', 'Market_Share_Pct': 12, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Unico grande produttore non-cinese. Processing Malaysia. US DoD partnership. Espansione Texas plant 2024.', 'Created_at': NOW, 'Updated_at': NOW},

    # --- SiC Substrates (mercato emergente, Wolfspeed dominante) ---
    {'Tier2_Supplier_ID': 'T2-018', 'Tier2_Supplier_Name': 'Wolfspeed Inc.', 'Material_Type': 'SiC Substrates', 'Material_Key': 'sic_substrates', 'Country': 'USA', 'Market_Share_Pct': 30, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Ex-Cree. Fab Durham NC. Leader 150mm SiC wafer. Nuovo megafab JP (nuova fabbrica) in costruzione Siler City NC. Cliente ST/Infineon.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-019', 'Tier2_Supplier_Name': 'SiCrystal GmbH (Rohm group)', 'Material_Type': 'SiC Substrates', 'Material_Key': 'sic_substrates', 'Country': 'Germany', 'Market_Share_Pct': 20, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Fab Nürnberg. Controllata Rohm Semiconductor. Principale fornitore ST Microelectronics per SiC MOSFET EV.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-020', 'Tier2_Supplier_Name': 'II-VI Advanced Materials (Coherent)', 'Material_Type': 'SiC Substrates', 'Material_Key': 'sic_substrates', 'Country': 'USA', 'Market_Share_Pct': 18, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Post-merger Coherent. Fab Easton PA. 150/200mm in roadmap. Recente investimento $300M per espansione.', 'Created_at': NOW, 'Updated_at': NOW},

    # --- Palladium (concentrazione Russia/Sudafrica ~64%) ---
    {'Tier2_Supplier_ID': 'T2-021', 'Tier2_Supplier_Name': 'Norilsk Nickel (Nornickel)', 'Material_Type': 'Palladium Wire', 'Material_Key': 'palladium_wire', 'Country': 'Russia', 'Market_Share_Pct': 42, 'Criticality': 'CRITICAL', 'Substitutability': 'Low', 'Notes': 'Norilsk Siberia. 40%+ palladio mondiale. Non sanzionato direttamente ma pagamenti SWIFT complicati post-2022. Usato bond wire MLCC.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-022', 'Tier2_Supplier_Name': 'Anglo American Platinum (Amplats)', 'Material_Type': 'Palladium Wire', 'Material_Key': 'palladium_wire', 'Country': 'South Africa', 'Market_Share_Pct': 22, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Bushveld Complex SA. Alternativa a Nornickel ma capacità limitata. Scioperi frequenti. Prezzo volatile.', 'Created_at': NOW, 'Updated_at': NOW},

    # --- CMP Slurry (USA e Giappone dominanti) ---
    {'Tier2_Supplier_ID': 'T2-023', 'Tier2_Supplier_Name': 'CMC Materials (Entegris)', 'Material_Type': 'CMP Slurry', 'Material_Key': 'cmp_slurry', 'Country': 'USA', 'Market_Share_Pct': 25, 'Criticality': 'HIGH', 'Substitutability': 'Medium', 'Notes': 'Acquisita Entegris 2023. Fab Aurora IL. CMP slurry per planarizzazione wafer. Ogni processo richiede qualifica specifica.', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-024', 'Tier2_Supplier_Name': 'Fujimi Incorporated', 'Material_Type': 'CMP Slurry', 'Material_Key': 'cmp_slurry', 'Country': 'Japan', 'Market_Share_Pct': 22, 'Criticality': 'HIGH', 'Substitutability': 'Medium', 'Notes': 'Fab Kiyosu (Giappone). Leader CMP slurry per ossido/metallo. TSMC/Samsung qualified. Filiale USA già operativa.', 'Created_at': NOW, 'Updated_at': NOW},

    # --- GaN Substrates ---
    {'Tier2_Supplier_ID': 'T2-025', 'Tier2_Supplier_Name': 'Nichia Corporation', 'Material_Type': 'GaN Substrates', 'Material_Key': 'gan_substrates', 'Country': 'Japan', 'Market_Share_Pct': 30, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Anan (Giappone). Leader GaN/LED. Brevetti aggressivi. GaN-on-SiC per RF (5G/radar).', 'Created_at': NOW, 'Updated_at': NOW},
    {'Tier2_Supplier_ID': 'T2-026', 'Tier2_Supplier_Name': 'Sumitomo Electric Industries', 'Material_Type': 'GaN Substrates', 'Material_Key': 'gan_substrates', 'Country': 'Japan', 'Market_Share_Pct': 25, 'Criticality': 'HIGH', 'Substitutability': 'Low', 'Notes': 'Osaka. GaN bulk crystal e wafer. Unico fornitore wafer GaN free-standing >2" a volume. Cliente power electronics EV.', 'Created_at': NOW, 'Updated_at': NOW},
])


# =============================================================================
# 6. COMPONENT_MATERIALS
# =============================================================================

component_materials = pd.DataFrame([
    # --- MCU NXP MKE02Z64VLD4 (90nm, mainstream) ---
    {'Part_Number': 'MKE02Z64VLD4', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 200mm', 'Tier2_Supplier_ID': 'T2-001', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Nodo 90nm, wafer 200mm', 'Created_at': NOW},
    {'Part_Number': 'MKE02Z64VLD4', 'Material_Key': 'photoresists', 'Material_Name': 'KrF Photoresist', 'Tier2_Supplier_ID': 'T2-008', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'KrF 248nm per nodo 90nm', 'Created_at': NOW},

    # --- MPU STM32MP157CAC3 (28nm, fab propria ST Crolles) ---
    {'Part_Number': 'STM32MP157CAC3', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-001', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Fab ST Crolles (Francia), 28nm FDSOI', 'Created_at': NOW},
    {'Part_Number': 'STM32MP157CAC3', 'Material_Key': 'photoresists', 'Material_Name': 'ArF Photoresist', 'Tier2_Supplier_ID': 'T2-007', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'ArF 193nm per nodo 28nm FDSOI', 'Created_at': NOW},
    {'Part_Number': 'STM32MP157CAC3', 'Material_Key': 'neon_gas', 'Material_Name': 'Neon Gas ultra-puro', 'Tier2_Supplier_ID': 'T2-011', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Laser ArF excimer richiede neon 99.999%', 'Created_at': NOW},

    # --- PMIC STPMIC1APQR ---
    {'Part_Number': 'STPMIC1APQR', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 200mm', 'Tier2_Supplier_ID': 'T2-001', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Fab ST Agrate Brianza, 130nm BCD', 'Created_at': NOW},
    {'Part_Number': 'STPMIC1APQR', 'Material_Key': 'photoresists', 'Material_Name': 'i-line Photoresist', 'Tier2_Supplier_ID': 'T2-008', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': '365nm i-line per nodo 130nm', 'Created_at': NOW},

    # --- Sensor BME280 (Bosch, MEMS) ---
    {'Part_Number': 'BME280', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 200mm MEMS', 'Tier2_Supplier_ID': 'T2-003', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Fab Bosch Reutlingen, processo MEMS proprietario', 'Created_at': NOW},

    # --- ESP32 (fabless Espressif, TSMC 40nm) ---
    {'Part_Number': 'ESP32-WROOM-32E', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-005', 'Custom_Concentration': None, 'Custom_Country': 'Taiwan', 'Notes': 'Fabless Espressif, produzione TSMC 40nm Taiwan', 'Created_at': NOW},
    {'Part_Number': 'ESP32-WROOM-32E', 'Material_Key': 'photoresists', 'Material_Name': 'ArF Photoresist', 'Tier2_Supplier_ID': 'T2-006', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'TSMC usa JSR per nodo 40nm', 'Created_at': NOW},
    {'Part_Number': 'ESP32-WROOM-32E', 'Material_Key': 'rare_earth', 'Material_Name': 'Rare Earth (antenna)', 'Tier2_Supplier_ID': 'T2-014', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Ossidi RE per componenti antenna integrata', 'Created_at': NOW},

    # --- MLCC Murata (palladio per elettrodi) ---
    {'Part_Number': 'GRM155R71C104KA88D', 'Material_Key': 'palladium_wire', 'Material_Name': 'Palladium (elettrodi interni)', 'Tier2_Supplier_ID': 'T2-021', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'MLCC X7R usa Pd/Ag per elettrodi interni. 0402 size ~0.2mg Pd per pz.', 'Created_at': NOW},
    {'Part_Number': 'GCM32ER71E106KA37', 'Material_Key': 'palladium_wire', 'Material_Name': 'Palladium (elettrodi interni)', 'Tier2_Supplier_ID': 'T2-021', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'MLCC 1210 alta tensione, contenuto Pd più alto per tensione di tenuta.', 'Created_at': NOW},
    {'Part_Number': 'C2012X7R1H104K', 'Material_Key': 'palladium_wire', 'Material_Name': 'Palladium (elettrodi interni)', 'Tier2_Supplier_ID': 'T2-021', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'TDK X7R 100nF, processo Ni-MLCC con tracce Pd.', 'Created_at': NOW},

    # --- MCU NXP S32K344 (ADAS, 40nm, fab esterna) ---
    {'Part_Number': 'S32K344', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-001', 'Custom_Concentration': None, 'Custom_Country': 'Taiwan', 'Notes': 'S32K3 prodotto TSMC 40nm (NXP fabless per questo nodo)', 'Created_at': NOW},
    {'Part_Number': 'S32K344', 'Material_Key': 'photoresists', 'Material_Name': 'ArF Photoresist', 'Tier2_Supplier_ID': 'T2-006', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'TSMC 40nm usa JSR/TOK ArF photoresist', 'Created_at': NOW},
    {'Part_Number': 'S32K344', 'Material_Key': 'neon_gas', 'Material_Name': 'Neon Gas ArF laser', 'Tier2_Supplier_ID': 'T2-010', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Produzione TSMC dipende da neon ucraino per laser ArF', 'Created_at': NOW},

    # --- MPU NXP S32G274A (16nm, TSMC) ---
    {'Part_Number': 'S32G274A', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-001', 'Custom_Concentration': None, 'Custom_Country': 'Taiwan', 'Notes': 'TSMC 16nm FinFET. Critico: wafer qualità premium per FinFET.', 'Created_at': NOW},
    {'Part_Number': 'S32G274A', 'Material_Key': 'photoresists', 'Material_Name': 'EUV/ArF-i Photoresist', 'Tier2_Supplier_ID': 'T2-006', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Multiple patterning ArF-i, fotoresist JSR qualificato TSMC N16', 'Created_at': NOW},
    {'Part_Number': 'S32G274A', 'Material_Key': 'neon_gas', 'Material_Name': 'Neon Gas ArF laser', 'Tier2_Supplier_ID': 'T2-010', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Litografia ArF multiple patterning = alto consumo neon', 'Created_at': NOW},

    # --- EYEQ5H Mobileye (Intel, 7nm TSMC — nodo avanzatissimo) ---
    {'Part_Number': 'EYEQ5H', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm EUV', 'Tier2_Supplier_ID': 'T2-001', 'Custom_Concentration': None, 'Custom_Country': 'Taiwan', 'Notes': 'TSMC N7P. Wafer top-purity per EUV. Concentrazione rischio massima.', 'Created_at': NOW},
    {'Part_Number': 'EYEQ5H', 'Material_Key': 'photoresists', 'Material_Name': 'EUV Photoresist', 'Tier2_Supplier_ID': 'T2-006', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'EUV resist JSR — unico fornitore qualificato TSMC N7. RISCHIO CRITICO.', 'Created_at': NOW},
    {'Part_Number': 'EYEQ5H', 'Material_Key': 'neon_gas', 'Material_Name': 'Neon Gas EUV/ArF', 'Tier2_Supplier_ID': 'T2-010', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'N7 usa sia EUV che ArF-i. Alto consumo neon per doppio sistema.', 'Created_at': NOW},

    # --- Memoria LPDDR4X Micron (fab Hiroshima) ---
    {'Part_Number': 'MT53E256M32D1DS-046', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-002', 'Custom_Concentration': None, 'Custom_Country': 'Japan', 'Notes': 'Fab Micron Hiroshima. SUMCO fornitore preferenziale Micron.', 'Created_at': NOW},
    {'Part_Number': 'MT53E256M32D1DS-046', 'Material_Key': 'photoresists', 'Material_Name': 'ArF-i Photoresist', 'Tier2_Supplier_ID': 'T2-007', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'DRAM usa ArF immersion + multiple patterning', 'Created_at': NOW},

    # --- Marvell 88Q2112 (TSMC, automotive Ethernet) ---
    {'Part_Number': '88Q2112-A2-NNP2I000', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-001', 'Custom_Concentration': None, 'Custom_Country': 'Taiwan', 'Notes': 'Marvell fabless, TSMC 28nm. Rischio concentrazione Taiwan.', 'Created_at': NOW},
    {'Part_Number': '88Q2112-A2-NNP2I000', 'Material_Key': 'neon_gas', 'Material_Name': 'Neon Gas', 'Tier2_Supplier_ID': 'T2-010', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'TSMC 28nm ArF — dipendente neon ucraino', 'Created_at': NOW},

    # --- Qualcomm QCA6174A-5 (TSMC 28nm, WiFi/BT) ---
    {'Part_Number': 'QCA6174A-5', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-001', 'Custom_Concentration': None, 'Custom_Country': 'Taiwan', 'Notes': 'Qualcomm fabless TSMC 28nm. Alta dipendenza Taiwan.', 'Created_at': NOW},
    {'Part_Number': 'QCA6174A-5', 'Material_Key': 'rare_earth', 'Material_Name': 'Rare Earth (RF filter)', 'Tier2_Supplier_ID': 'T2-014', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'BAW/SAW filter RF usa ossidi lantanio/cerio. Dipendenza Cina per REE.', 'Created_at': NOW},

    # --- Quectel EC25-E (TSMC 28nm, LTE modem) ---
    {'Part_Number': 'EC25-E', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-005', 'Custom_Concentration': None, 'Custom_Country': 'Taiwan', 'Notes': 'Qualcomm MDM9607 inside, prodotto TSMC Taiwan.', 'Created_at': NOW},
    {'Part_Number': 'EC25-E', 'Material_Key': 'rare_earth', 'Material_Name': 'Rare Earth (antenna RF)', 'Tier2_Supplier_ID': 'T2-014', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'LTE antenna richiedere materiali RE per ceramica risonante.', 'Created_at': NOW},

    # --- Renesas MPU R9A07G044 (fab propria Naka, 28nm) ---
    {'Part_Number': 'R9A07G044L23GBG', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-002', 'Custom_Concentration': None, 'Custom_Country': 'Japan', 'Notes': 'Fab Renesas Naka (Giappone). SUMCO fornitore wafer Renesas.', 'Created_at': NOW},
    {'Part_Number': 'R9A07G044L23GBG', 'Material_Key': 'photoresists', 'Material_Name': 'ArF Photoresist', 'Tier2_Supplier_ID': 'T2-007', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Renesas usa TOK per litografia ArF nodo 28nm', 'Created_at': NOW},

    # --- Passivo induttore TDK / Vishay (ferrite/RE) ---
    {'Part_Number': 'VLS252015HBX-1R0M', 'Material_Key': 'rare_earth', 'Material_Name': 'Ferrite (ossidi Fe/Mn)', 'Tier2_Supplier_ID': 'T2-016', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Induttore TDK usa ferrite sinterizzata. Mn-Zn ferrite con ossidi da Cina.', 'Created_at': NOW},
    {'Part_Number': 'IHLP2525CZER1R0M11', 'Material_Key': 'rare_earth', 'Material_Name': 'Ferrite (ossidi Fe/Ni)', 'Tier2_Supplier_ID': 'T2-016', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'Induttore Vishay IHLP, core ferrite ad alta permeabilità.', 'Created_at': NOW},

    # --- NOR Flash Macronix (fab propria Taiwan) ---
    {'Part_Number': 'MX25U25645G', 'Material_Key': 'silicon_wafers', 'Material_Name': 'Silicon Wafers 300mm', 'Tier2_Supplier_ID': 'T2-005', 'Custom_Concentration': None, 'Custom_Country': 'Taiwan', 'Notes': 'Macronix fab Hsinchu. Rischio Taiwan diretto.', 'Created_at': NOW},
    {'Part_Number': 'MX25U25645G', 'Material_Key': 'photoresists', 'Material_Name': 'ArF Photoresist', 'Tier2_Supplier_ID': 'T2-007', 'Custom_Concentration': None, 'Custom_Country': None, 'Notes': 'NOR Flash 55nm usa ArF. TOK qualificato per Macronix.', 'Created_at': NOW},
])


# =============================================================================
# 7. SUPPLIER_PROFILES
# =============================================================================

import json

supplier_profiles = pd.DataFrame([
    # --- TSMC (il fornitore più critico — fabless Qualcomm/Marvell/Espressif/Mobileye) ---
    {
        'Supplier_ID': 'SP-TSMC',
        'Supplier_Name': 'TSMC (Taiwan Semiconductor Manufacturing)',
        'Primary_Fab': 'Fab 18 / Fab 12 (N7/N5), Fab 14 (N16/N28), Fab 6 (N40)',
        'Primary_Fab_Country': 'Taiwan',
        'Wafer_Source': 'Shin-Etsu Chemical, SUMCO',
        'Key_Materials_Override': json.dumps({
            'silicon_wafers': {'country': 'Japan', 'concentration': 0.92},
            'photoresists': {'country': 'Japan', 'concentration': 0.95},
            'neon_gas': {'country': 'Ukraine', 'concentration': 0.75},
            'cmp_slurry': {'country': 'USA', 'concentration': 0.50}
        }),
        'Notes': 'Produce EYEQ5H(N7), S32G274A(N16), S32K344(N40), 88Q2112(N28), QCA6174A(N28), ESP32(N40). Concentrazione rischio più alta del database.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    # --- STMicroelectronics (fab proprie Crolles/Agrate) ---
    {
        'Supplier_ID': 'SP-ST',
        'Supplier_Name': 'STMicroelectronics',
        'Primary_Fab': 'Crolles (28nm FDSOI), Agrate Brianza (130nm BCD), Catania (SiC)',
        'Primary_Fab_Country': 'France',
        'Wafer_Source': 'Siltronic AG (Germania), Shin-Etsu Chemical',
        'Key_Materials_Override': json.dumps({
            'silicon_wafers': {'country': 'Germany', 'concentration': 0.45},
            'photoresists': {'country': 'Japan', 'concentration': 0.85},
            'neon_gas': {'country': 'France', 'concentration': 0.40},
            'sic_substrates': {'country': 'Germany', 'concentration': 0.65}
        }),
        'Notes': 'Fab proprie = minor dipendenza Taiwan. 28nm FDSOI unico al mondo (solo ST+Samsung). SiC fab Catania per automotive EV.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    # --- NXP Semiconductors ---
    {
        'Supplier_ID': 'SP-NXP',
        'Supplier_Name': 'NXP Semiconductors',
        'Primary_Fab': 'Nijmegen (NL, 0.18um), Hamburg (DE), Austin TX (USA), TSMC (N40/N16 outsourced)',
        'Primary_Fab_Country': 'Netherlands',
        'Wafer_Source': 'Siltronic AG, GlobalWafers',
        'Key_Materials_Override': json.dumps({
            'silicon_wafers': {'country': 'Germany', 'concentration': 0.40},
            'photoresists': {'country': 'Japan', 'concentration': 0.80},
            'neon_gas': {'country': 'Germany', 'concentration': 0.35},
        }),
        'Notes': 'Mix fab proprie (legacy node) + TSMC (nodi avanzati). S32K344 e S32G274A outsourciate TSMC Taiwan. MKE02Z prodotto Nijmegen.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    # --- Infineon Technologies ---
    {
        'Supplier_ID': 'SP-IFX',
        'Supplier_Name': 'Infineon Technologies',
        'Primary_Fab': 'Dresden (300mm, 65nm), Regensburg (200mm), Malacca (Malaysia)',
        'Primary_Fab_Country': 'Germany',
        'Wafer_Source': 'Siltronic AG (socio strategico), Shin-Etsu',
        'Key_Materials_Override': json.dumps({
            'silicon_wafers': {'country': 'Germany', 'concentration': 0.55},
            'photoresists': {'country': 'Japan', 'concentration': 0.80},
            'neon_gas': {'country': 'Germany', 'concentration': 0.30},
            'sic_substrates': {'country': 'Germany', 'concentration': 0.40}
        }),
        'Notes': 'Fab Europa + Malaysia = profilo geopolitico migliore. SiC power: usa SiCrystal (Germania). TLE9251VLE prodotto Dresden.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    # --- Texas Instruments ---
    {
        'Supplier_ID': 'SP-TI',
        'Supplier_Name': 'Texas Instruments',
        'Primary_Fab': 'DMOS6 Dallas TX, RFAB Richardson TX, BPII Lehi UT, Aizu (Giappone)',
        'Primary_Fab_Country': 'USA',
        'Wafer_Source': 'Multiple (SK Siltron, GlobalWafers)',
        'Key_Materials_Override': json.dumps({
            'silicon_wafers': {'country': 'USA', 'concentration': 0.35},
            'photoresists': {'country': 'Japan', 'concentration': 0.70},
            'neon_gas': {'country': 'USA', 'concentration': 0.30},
        }),
        'Notes': 'Maggiore IDM con fab proprie USA/Giappone. Strategia 300mm interna = costi bassi, minor dipendenza esterna. TPS62840/TPS65263 fabbricati USA.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    # --- Renesas Electronics ---
    {
        'Supplier_ID': 'SP-REN',
        'Supplier_Name': 'Renesas Electronics',
        'Primary_Fab': 'Naka (300mm, 40nm), Kofu (200mm), Shiga (200mm)',
        'Primary_Fab_Country': 'Japan',
        'Wafer_Source': 'SUMCO Corporation',
        'Key_Materials_Override': json.dumps({
            'silicon_wafers': {'country': 'Japan', 'concentration': 0.85},
            'photoresists': {'country': 'Japan', 'concentration': 0.90},
            'neon_gas': {'country': 'Ukraine', 'concentration': 0.60},
        }),
        'Notes': 'Fab Giappone = dipendenza forte da Tier-2 giapponesi (wafer+resist). Terremoto/tsunami rischio operativo. Alta qualificazione automotive AEC-Q100.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    # --- Mobileye (Intel) — chip esclusivo EYEQ ---
    {
        'Supplier_ID': 'SP-MBY',
        'Supplier_Name': 'Mobileye (Intel Corporation)',
        'Primary_Fab': 'TSMC Fab 18 (N7P) — outsourced totalmente',
        'Primary_Fab_Country': 'Taiwan',
        'Wafer_Source': 'Shin-Etsu Chemical (via TSMC)',
        'Key_Materials_Override': json.dumps({
            'silicon_wafers': {'country': 'Japan', 'concentration': 0.95},
            'photoresists': {'country': 'Japan', 'concentration': 0.98},
            'neon_gas': {'country': 'Ukraine', 'concentration': 0.80},
        }),
        'Notes': 'EYEQ5H: completamente dipendente TSMC Taiwan N7P. RISCHIO CRITICO: fab unica, distributore unico (Arrow), alt source non qualificata. Tripla concentrazione.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
    # --- Qualcomm (fabless, principalmente TSMC) ---
    {
        'Supplier_ID': 'SP-QCOM',
        'Supplier_Name': 'Qualcomm Incorporated',
        'Primary_Fab': 'TSMC N28 (QCA6174), TSMC N7/N5 (Snapdragon) — fabless',
        'Primary_Fab_Country': 'Taiwan',
        'Wafer_Source': 'Shin-Etsu Chemical (via TSMC)',
        'Key_Materials_Override': json.dumps({
            'silicon_wafers': {'country': 'Japan', 'concentration': 0.92},
            'photoresists': {'country': 'Japan', 'concentration': 0.95},
            'neon_gas': {'country': 'Ukraine', 'concentration': 0.75},
            'rare_earth': {'country': 'China', 'concentration': 0.70}
        }),
        'Notes': 'Fabless totale. QCA6174A prodotto TSMC 28nm Taiwan. RF filter usa RE cinesi. Accordo distribuzione esclusivo Future Electronics.',
        'Created_at': NOW, 'Updated_at': NOW,
    },
])


# =============================================================================
# SCRITTURA NEL DATABASE
# =============================================================================

def write_sheet(df: pd.DataFrame, sheet_name: str):
    """Aggiunge/sostituisce un foglio nel database esistente."""
    with pd.ExcelWriter(
        DB_PATH,
        engine='openpyxl',
        mode='a',
        if_sheet_exists='replace'
    ) as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f'  OK: {sheet_name} — {len(df)} righe scritte')


if __name__ == '__main__':
    print(f'Popolo {DB_PATH} con dati realistici v4.0...\n')

    write_sheet(ems_providers,       'EMS_Providers')
    write_sheet(distributors,        'Distributors')
    write_sheet(part_distributors,   'Part_Distributors')
    write_sheet(alt_sources,         'Alt_Sources')
    write_sheet(tier2_suppliers,     'Tier2_Suppliers')
    write_sheet(component_materials, 'Component_Materials')
    write_sheet(supplier_profiles,   'Supplier_Profiles')

    print('\nVerifica fogli risultanti:')
    import openpyxl
    wb = openpyxl.load_workbook(DB_PATH, read_only=True)
    for sheet in wb.sheetnames:
        df = pd.read_excel(DB_PATH, sheet_name=sheet).dropna(how='all')
        print(f'  {sheet}: {len(df)} righe')
    wb.close()

    print('\nDone. Avvia: python -m streamlit run app.py')
