"""
Part Number Lookup - Database Management
=========================================
Modulo per la gestione del database Excel dei Part Numbers.

Fornisce funzionalità per:
- Lookup di part numbers nel database
- Aggiunta di nuovi part numbers
- Gestione dati specifici per cliente
- Ricerca e modifica di record esistenti

Uso:
    from pn_lookup import PartNumberDatabase

    db = PartNumberDatabase('part_numbers_db.xlsx')
    data = db.lookup_part_number('STM32F103C8T6', client_id='CLIENTE_001')
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import shutil


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

DEFAULT_DB_NAME = str(Path(__file__).parent.parent / 'data' / 'part_numbers_db.xlsx')

# Nomi dei fogli Excel
SHEET_PART_NUMBERS = 'Part_Numbers'
SHEET_CLIENT_DATA = 'Client_Data'
SHEET_CLIENTS = 'Clients'
SHEET_TIER2_SUPPLIERS = 'Tier2_Suppliers'
SHEET_COMPONENT_MATERIALS = 'Component_Materials'
# v4.0 - Filiera commerciale
SHEET_EMS_PROVIDERS = 'EMS_Providers'
SHEET_DISTRIBUTORS = 'Distributors'
SHEET_PART_DISTRIBUTORS = 'Part_Distributors'
SHEET_ALT_SOURCES = 'Alt_Sources'
SHEET_SUPPLIER_PROFILES = 'Supplier_Profiles'

# Colonne obbligatorie per ogni foglio
PART_NUMBERS_COLUMNS = [
    'Part Number',
    'Supplier Name',
    'Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)',
    'Country of Manufacturing Plant 1',
    'Country of Manufacturing Plant 2',
    'Country of Manufacturing Plant 3',
    'Country of Manufacturing Plant 4',
    'Supplier Lead Time (weeks)',
    'Proprietary (Y/N)**',
    'Commodity (Y/N)*',
    'Stand-Alone Functional Device (Y/N)',
    'Weeks to qualify',
    'Unit Price ($)',
    'Specify Certification/Qualification',
    'In case answer on Column C is Y, Which other device in the BOM is necessary to run the PN on Column B? (e.g. PMIC for MPU, Memory for MPU)',
    # v3.0 - Geo Risk Frontend/Backend
    'Frontend_Country',
    'Backend_Country',
    'Technology_Node',
    'Plant_1_Name',
    'Plant_2_Name',
    'Plant_3_Name',
    'Plant_4_Name',
    'EMS_Used',
    'EMS_Name',
    'EMS_Location',
    # v3.0 - Switching Cost
    'SW_Code_Size_KB',
    'Memory_Type',
    'OS_Type',
    'Wireless_Protocol',
    # v3.1 - Extended Risk Fields
    'EOL_Status',                    # Active / NRND / Last_Buy / EOL / Obsolete
    'Number_of_Alternative_Sources', # 0, 1, 2, 3+
    'Supplier_Financial_Health',     # A / B / C / D
    'MTBF_Hours',                    # Mean Time Between Failures
    'Automotive_Grade',              # None / AEC-Q100 / AEC-Q101 / AEC-Q200
    'Last_Price_Increase_Pct',       # % ultimo aumento prezzo
    'Allocation_Status',             # Normal / Constrained / Allocated
    'Package_Type',                  # QFP / BGA / WLCSP / QFN / SOP / DIP / CSP
    # Timestamps
    'Created_at',
    'Updated_at'
]

CLIENT_DATA_COLUMNS = [
    'Client_ID',
    'Part Number',
    'How Many Device of this specific PN are in the BOM?',
    'If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units',
    'Custom Supplier Lead Time (weeks)',
    'Notes'
]

CLIENTS_COLUMNS = [
    'Client_ID',
    'Client_Name',
    'Default_Run_Rate',
    'Created_at'
]

TIER2_SUPPLIERS_COLUMNS = [
    'Tier2_Supplier_ID',
    'Tier2_Supplier_Name',
    'Material_Type',
    'Material_Key',
    'Country',
    'Market_Share_Pct',
    'Criticality',
    'Substitutability',
    'Notes',
    'Created_at',
    'Updated_at',
]

COMPONENT_MATERIALS_COLUMNS = [
    'Part_Number',
    'Material_Key',
    'Material_Name',
    'Tier2_Supplier_ID',
    'Custom_Concentration',
    'Custom_Country',
    'Notes',
    'Created_at',
]

# v4.0 - Nuovi fogli filiera commerciale
EMS_PROVIDERS_COLUMNS = [
    'EMS_ID',
    'EMS_Name',
    'Country',
    'Financial_Health',       # A / B / C / D
    'Capacity_Utilization_Pct',  # 0-100
    'Certifications',         # Comma-separated: ISO9001, IATF16949, AS9100, IPC-J-STD-001
    'Backup_Sites_Count',     # Numero siti di backup
    'Years_Business',         # Anni di attività
    'Notes',
    'Created_at',
    'Updated_at',
]

DISTRIBUTORS_COLUMNS = [
    'Distributor_ID',
    'Name',
    'Country',
    'Financial_Health',           # A / B / C / D
    'Lead_Time_Markup_Weeks',     # Settimane extra sul lead time fornitore
    'Stock_Level_Weeks_Coverage', # Settimane di stock mediamente disponibili
    'Certifications',             # AS9120, ISO9001, ecc.
    'Backup_Count',               # Numero distributori alternativi disponibili
    'Notes',
    'Created_at',
    'Updated_at',
]

PART_DISTRIBUTORS_COLUMNS = [
    'Part_Number',
    'Distributor_ID',
    'Priority',        # Primary / Secondary
    'Allocation_Pct',  # % acquistata da questo distributore
    'Created_at',
]

ALT_SOURCES_COLUMNS = [
    'Part_Number',
    'Supplier_Name',
    'Frontend_Country',
    'Backend_Country',
    'Lead_Time_Weeks',
    'Financial_Health',       # A / B / C / D
    'Qualification_Status',   # Qualified / In_Progress / Not_Started
    'Allocation_Pct',         # % attuale di acquisto da questa fonte
    'Notes',
    'Created_at',
]

SUPPLIER_PROFILES_COLUMNS = [
    'Supplier_ID',
    'Supplier_Name',
    'Primary_Fab',          # Nome fab (es. TSMC Fab 18)
    'Primary_Fab_Country',  # Paese fab
    'Wafer_Source',         # Fornitore wafer (es. Shin-Etsu)
    'Key_Materials_Override',  # JSON: {material_key: {country: %, concentration: float}}
    'Notes',
    'Created_at',
    'Updated_at',
]


# =============================================================================
# CLASSE PRINCIPALE
# =============================================================================

class PartNumberDatabase:
    """
    Gestore del database Excel dei Part Numbers.

    Offre metodi per lookup, inserimento, modifica e ricerca di part numbers,
    con supporto per dati specifici per cliente.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Inizializza il database.

        Args:
            db_path: Percorso del file Excel. Se None, usa il default.
        """
        self.db_path = Path(db_path) if db_path else Path(DEFAULT_DB_NAME)
        self._ensure_database_exists()

    # -------------------------------------------------------------------------
    # METODI PRIVATI
    # -------------------------------------------------------------------------

    def _ensure_database_exists(self) -> None:
        """Crea il database se non esiste."""
        if not self.db_path.exists():
            self._create_empty_database()

    def _create_empty_database(self) -> None:
        """Crea un database vuoto con la struttura corretta."""
        with pd.ExcelWriter(self.db_path, engine='openpyxl') as writer:
            pd.DataFrame(columns=PART_NUMBERS_COLUMNS).to_excel(
                writer, sheet_name=SHEET_PART_NUMBERS, index=False
            )
            pd.DataFrame(columns=CLIENT_DATA_COLUMNS).to_excel(
                writer, sheet_name=SHEET_CLIENT_DATA, index=False
            )
            pd.DataFrame(columns=CLIENTS_COLUMNS).to_excel(
                writer, sheet_name=SHEET_CLIENTS, index=False
            )
            pd.DataFrame(columns=TIER2_SUPPLIERS_COLUMNS).to_excel(
                writer, sheet_name=SHEET_TIER2_SUPPLIERS, index=False
            )
            pd.DataFrame(columns=COMPONENT_MATERIALS_COLUMNS).to_excel(
                writer, sheet_name=SHEET_COMPONENT_MATERIALS, index=False
            )
            # v4.0 - Filiera commerciale
            pd.DataFrame(columns=EMS_PROVIDERS_COLUMNS).to_excel(
                writer, sheet_name=SHEET_EMS_PROVIDERS, index=False
            )
            pd.DataFrame(columns=DISTRIBUTORS_COLUMNS).to_excel(
                writer, sheet_name=SHEET_DISTRIBUTORS, index=False
            )
            pd.DataFrame(columns=PART_DISTRIBUTORS_COLUMNS).to_excel(
                writer, sheet_name=SHEET_PART_DISTRIBUTORS, index=False
            )
            pd.DataFrame(columns=ALT_SOURCES_COLUMNS).to_excel(
                writer, sheet_name=SHEET_ALT_SOURCES, index=False
            )
            pd.DataFrame(columns=SUPPLIER_PROFILES_COLUMNS).to_excel(
                writer, sheet_name=SHEET_SUPPLIER_PROFILES, index=False
            )

    def _load_sheet(self, sheet_name: str) -> pd.DataFrame:
        """Carica un foglio dal database."""
        try:
            df = pd.read_excel(self.db_path, sheet_name=sheet_name)
            # Rimuovi righe completamente vuote
            df = df.dropna(how='all')
            return df
        except Exception:
            # Se il foglio non esiste o è vuoto, restituisci DataFrame vuoto
            return pd.DataFrame()

    def _save_sheet(self, df: pd.DataFrame, sheet_name: str) -> None:
        """Salva un foglio nel database."""
        # Prima leggi tutti i fogli esistenti
        with pd.ExcelWriter(self.db_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    def _normalize_pn(self, pn: str) -> str:
        """Normalizza un part number per il confronto."""
        return str(pn).strip().upper()

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - LOOKUP
    # -------------------------------------------------------------------------

    def lookup_part_number(self, pn: str, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Cerca un part number nel database e restituisce i dati combinati.

        La logica di combinazione è:
        1. Dati globali dal foglio Part_Numbers (base)
        2. Dati specifici cliente da Client_Data (sovrascrivono/aggiungono)

        Args:
            pn: Part Number da cercare
            client_id: ID del cliente (opzionale, per dati specifici)

        Returns:
            Dizionario con tutti i dati del componente, o None se non trovato
        """
        pn_normalized = self._normalize_pn(pn)

        # 1. Cerca dati globali
        df_part_numbers = self._load_sheet(SHEET_PART_NUMBERS)

        if df_part_numbers.empty:
            return None

        # Cerca il part number (case-insensitive)
        mask = df_part_numbers['Part Number'].astype(str).str.upper() == pn_normalized
        matching_rows = df_part_numbers[mask]

        if matching_rows.empty:
            return None

        # Prendi il primo match
        global_data = matching_rows.iloc[0].to_dict()

        # 2. Se specificato cliente, cerca dati specifici
        if client_id:
            df_client_data = self._load_sheet(SHEET_CLIENT_DATA)

            if not df_client_data.empty:
                mask_client = (
                    (df_client_data['Part Number'].astype(str).str.upper() == pn_normalized) &
                    (df_client_data['Client_ID'].astype(str).str.upper() == client_id.upper())
                )
                client_rows = df_client_data[mask_client]

                if not client_rows.empty:
                    client_data = client_rows.iloc[0].to_dict()

                    # Sovrascrivi/aggiungi dati cliente
                    if pd.notna(client_data.get('How Many Device of this specific PN are in the BOM?')):
                        global_data['How Many Device of this specific PN are in the BOM?'] = client_data[
                            'How Many Device of this specific PN are in the BOM?'
                        ]
                    if pd.notna(client_data.get('If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units')):
                        global_data['If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units'] = client_data[
                            'If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units'
                        ]
                    if pd.notna(client_data.get('Custom Supplier Lead Time (weeks)')):
                        global_data['Supplier Lead Time (weeks)'] = client_data['Custom Supplier Lead Time (weeks)']

        return global_data

    def lookup_batch(self, pns: List[str], client_id: Optional[str] = None) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Cerca più part numbers in una volta.

        Args:
            pns: Lista di Part Numbers
            client_id: ID del cliente (opzionale)

        Returns:
            Dizionario {part_number: dati} con None per i PN non trovati
        """
        results = {}
        for pn in pns:
            results[pn] = self.lookup_part_number(pn, client_id)
        return results

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - INSERIMENTO/MODIFICA
    # -------------------------------------------------------------------------

    def add_part_number(self, pn: str, data: Dict[str, Any], client_id: Optional[str] = None) -> bool:
        """
        Aggiunge o aggiorna un part number nel database.

        Args:
            pn: Part Number
            data: Dizionario con i dati del componente
            client_id: ID cliente (opzionale, per dati specifici cliente)

        Returns:
            True se successo, False altrimenti
        """
        try:
            pn_normalized = self._normalize_pn(pn)
            df_part_numbers = self._load_sheet(SHEET_PART_NUMBERS)

            # Separa dati globali da dati cliente
            global_data = {}
            client_data = {'Part Number': pn_normalized}

            if client_id:
                client_data['Client_ID'] = client_id.upper()

            for key, value in data.items():
                if key in ['How Many Device of this specific PN are in the BOM?',
                          'If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units',
                          'Custom Supplier Lead Time (weeks)', 'Notes']:
                    # Dati specifici cliente
                    client_data[key] = value
                else:
                    # Dati globali
                    global_data[key] = value

            # Aggiungi timestamp
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            global_data['Part Number'] = pn_normalized
            global_data['Updated_at'] = now

            # Aggiorna o inserisci dati globali
            mask = df_part_numbers['Part Number'].astype(str).str.upper() == pn_normalized

            if mask.any():
                # Update esistente
                for col in df_part_numbers.columns:
                    if col in global_data:
                        df_part_numbers.loc[mask, col] = global_data[col]
            else:
                # Insert nuovo
                global_data['Created_at'] = now
                new_row = pd.DataFrame([global_data])
                df_part_numbers = pd.concat([df_part_numbers, new_row], ignore_index=True)

            self._save_sheet(df_part_numbers, SHEET_PART_NUMBERS)

            # Se ci sono dati cliente, aggiorna anche Client_Data
            if client_id and any(v is not None for k, v in client_data.items() if k not in ['Part Number', 'Client_ID']):
                df_client_data = self._load_sheet(SHEET_CLIENT_DATA)

                mask_client = (
                    (df_client_data['Part Number'].astype(str).str.upper() == pn_normalized) &
                    (df_client_data['Client_ID'].astype(str).str.upper() == client_id.upper())
                )

                if mask_client.any():
                    # Update esistente
                    for col in df_client_data.columns:
                        if col in client_data:
                            df_client_data.loc[mask_client, col] = client_data[col]
                else:
                    # Insert nuovo
                    new_row = pd.DataFrame([client_data])
                    df_client_data = pd.concat([df_client_data, new_row], ignore_index=True)

                self._save_sheet(df_client_data, SHEET_CLIENT_DATA)

            return True

        except Exception as e:
            print(f"Errore nell'aggiungere il part number: {e}")
            return False

    def search_similar(self, pattern: str) -> List[Dict[str, Any]]:
        """
        Cerca part numbers che contengono il pattern specificato.

        Args:
            pattern: Pattern di ricerca (case-insensitive)

        Returns:
            Lista di dizionari con i part numbers trovati
        """
        df = self._load_sheet(SHEET_PART_NUMBERS)

        if df.empty:
            return []

        pattern_upper = pattern.upper()
        mask = df['Part Number'].astype(str).str.upper().str.contains(pattern_upper, na=False)

        matching = df[mask]
        return matching.to_dict('records')

    def get_all_part_numbers(self) -> List[str]:
        """Restituisce la lista di tutti i part numbers nel database."""
        df = self._load_sheet(SHEET_PART_NUMBERS)

        if df.empty:
            return []

        return df['Part Number'].dropna().unique().tolist()

    def remove_part_number(self, pn: str, client_id: Optional[str] = None) -> bool:
        """
        Rimuove un part number dal database.

        Args:
            pn: Part Number da rimuovere
            client_id: Se specificato, rimuove solo i dati cliente.
                      Se None, rimuove completamente il part number.

        Returns:
            True se successo, False altrimenti
        """
        try:
            pn_normalized = self._normalize_pn(pn)

            if client_id:
                # Rimuovi solo dati specifici cliente
                df_client_data = self._load_sheet(SHEET_CLIENT_DATA)

                if not df_client_data.empty:
                    mask = (
                        (df_client_data['Part Number'].astype(str).str.upper() == pn_normalized) &
                        (df_client_data['Client_ID'].astype(str).str.upper() == client_id.upper())
                    )
                    df_client_data = df_client_data[~mask]
                    self._save_sheet(df_client_data, SHEET_CLIENT_DATA)

            else:
                # Rimuovi completamente da entrambi i fogli
                df_part_numbers = self._load_sheet(SHEET_PART_NUMBERS)

                if not df_part_numbers.empty:
                    mask = df_part_numbers['Part Number'].astype(str).str.upper() == pn_normalized
                    df_part_numbers = df_part_numbers[~mask]
                    self._save_sheet(df_part_numbers, SHEET_PART_NUMBERS)

                # Rimuovi anche tutti i dati cliente associati
                df_client_data = self._load_sheet(SHEET_CLIENT_DATA)

                if not df_client_data.empty:
                    mask = df_client_data['Part Number'].astype(str).str.upper() == pn_normalized
                    df_client_data = df_client_data[~mask]
                    self._save_sheet(df_client_data, SHEET_CLIENT_DATA)

            return True

        except Exception as e:
            print(f"Errore nella rimozione del part number: {e}")
            return False

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - GESTIONE CLIENTI
    # -------------------------------------------------------------------------

    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Restituisce la lista di tutti i clienti."""
        df = self._load_sheet(SHEET_CLIENTS)

        if df.empty:
            return []

        return df.to_dict('records')

    def add_client(self, client_id: str, client_name: str, default_run_rate: int = 5000) -> bool:
        """
        Aggiunge o aggiorna un cliente.

        Args:
            client_id: ID univoco del cliente
            client_name: Nome del cliente
            default_run_rate: Run rate di default

        Returns:
            True se successo, False altrimenti
        """
        try:
            df_clients = self._load_sheet(SHEET_CLIENTS)

            client_id_upper = client_id.upper()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            new_data = {
                'Client_ID': client_id_upper,
                'Client_Name': client_name,
                'Default_Run_Rate': default_run_rate,
                'Created_at': now
            }

            mask = df_clients['Client_ID'].astype(str).str.upper() == client_id_upper

            if mask.any():
                # Update
                for col in df_clients.columns:
                    if col in new_data and col != 'Created_at':
                        df_clients.loc[mask, col] = new_data[col]
            else:
                # Insert
                new_row = pd.DataFrame([new_data])
                df_clients = pd.concat([df_clients, new_row], ignore_index=True)

            self._save_sheet(df_clients, SHEET_CLIENTS)
            return True

        except Exception as e:
            print(f"Errore nell'aggiungere il cliente: {e}")
            return False

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Restituisce i dati di un cliente."""
        df_clients = self._load_sheet(SHEET_CLIENTS)

        if df_clients.empty:
            return None

        mask = df_clients['Client_ID'].astype(str).str.upper() == client_id.upper()

        if mask.any():
            return df_clients[mask].iloc[0].to_dict()

        return None

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - MIGRAZIONE DATABASE
    # -------------------------------------------------------------------------

    def migrate_database(self) -> bool:
        """
        Migra il database aggiungendo le nuove colonne v3.0 senza perdere dati.

        Returns:
            True se la migrazione è riuscita o non necessaria, False altrimenti.
        """
        try:
            df_pn = self._load_sheet(SHEET_PART_NUMBERS)
            if df_pn.empty:
                return True

            changed = False
            for col in PART_NUMBERS_COLUMNS:
                if col not in df_pn.columns:
                    df_pn[col] = ''
                    changed = True

            if changed:
                self._save_sheet(df_pn, SHEET_PART_NUMBERS)

            # Migrazione fogli Tier-2/3
            df_t2 = self._load_sheet(SHEET_TIER2_SUPPLIERS)
            if df_t2.empty or not all(c in df_t2.columns for c in TIER2_SUPPLIERS_COLUMNS):
                df_t2 = pd.DataFrame(columns=TIER2_SUPPLIERS_COLUMNS)
                self._save_sheet(df_t2, SHEET_TIER2_SUPPLIERS)

            df_cm = self._load_sheet(SHEET_COMPONENT_MATERIALS)
            if df_cm.empty or not all(c in df_cm.columns for c in COMPONENT_MATERIALS_COLUMNS):
                df_cm = pd.DataFrame(columns=COMPONENT_MATERIALS_COLUMNS)
                self._save_sheet(df_cm, SHEET_COMPONENT_MATERIALS)

            # v4.0 - Migrazione nuovi fogli filiera commerciale
            for sheet_name, columns in [
                (SHEET_EMS_PROVIDERS, EMS_PROVIDERS_COLUMNS),
                (SHEET_DISTRIBUTORS, DISTRIBUTORS_COLUMNS),
                (SHEET_PART_DISTRIBUTORS, PART_DISTRIBUTORS_COLUMNS),
                (SHEET_ALT_SOURCES, ALT_SOURCES_COLUMNS),
                (SHEET_SUPPLIER_PROFILES, SUPPLIER_PROFILES_COLUMNS),
            ]:
                df_new = self._load_sheet(sheet_name)
                if df_new.empty or not all(c in df_new.columns for c in columns):
                    # Preserva dati esistenti aggiungendo colonne mancanti
                    if not df_new.empty:
                        for col in columns:
                            if col not in df_new.columns:
                                df_new[col] = ''
                    else:
                        df_new = pd.DataFrame(columns=columns)
                    self._save_sheet(df_new, sheet_name)

            return True
        except Exception as e:
            print(f"Errore nella migrazione del database: {e}")
            return False

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - TIER 2 SUPPLIERS
    # -------------------------------------------------------------------------

    def get_tier2_suppliers(self, material_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Restituisce fornitori Tier-2, opzionalmente filtrati per material_key."""
        df = self._load_sheet(SHEET_TIER2_SUPPLIERS)
        if df.empty:
            return []
        if material_key:
            mask = df['Material_Key'].astype(str).str.upper() == material_key.upper()
            return df[mask].to_dict('records')
        return df.to_dict('records')

    def add_tier2_supplier(self, data: Dict[str, Any]) -> bool:
        """Aggiunge o aggiorna un fornitore Tier-2."""
        try:
            df = self._load_sheet(SHEET_TIER2_SUPPLIERS)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Auto-genera ID se non fornito
            supplier_id = data.get('Tier2_Supplier_ID', '')
            if not supplier_id:
                existing_ids = df['Tier2_Supplier_ID'].tolist() if not df.empty else []
                max_num = 0
                for eid in existing_ids:
                    try:
                        num = int(str(eid).replace('T2S_', ''))
                        max_num = max(max_num, num)
                    except (ValueError, TypeError):
                        pass
                supplier_id = f"T2S_{max_num + 1:03d}"

            data['Tier2_Supplier_ID'] = supplier_id
            data['Updated_at'] = now

            if df.empty:
                data['Created_at'] = now
                new_row = pd.DataFrame([data])
                df = pd.concat([df, new_row], ignore_index=True)
            else:
                mask = df['Tier2_Supplier_ID'].astype(str) == str(supplier_id)
                if mask.any():
                    for col in df.columns:
                        if col in data and col != 'Created_at':
                            df.loc[mask, col] = data[col]
                else:
                    data['Created_at'] = now
                    new_row = pd.DataFrame([data])
                    df = pd.concat([df, new_row], ignore_index=True)

            self._save_sheet(df, SHEET_TIER2_SUPPLIERS)
            return True
        except Exception as e:
            print(f"Errore nell'aggiungere fornitore Tier-2: {e}")
            return False

    def remove_tier2_supplier(self, supplier_id: str) -> bool:
        """Rimuove un fornitore Tier-2."""
        try:
            df = self._load_sheet(SHEET_TIER2_SUPPLIERS)
            if df.empty:
                return False
            mask = df['Tier2_Supplier_ID'].astype(str) == str(supplier_id)
            df = df[~mask]
            self._save_sheet(df, SHEET_TIER2_SUPPLIERS)
            return True
        except Exception as e:
            print(f"Errore nella rimozione fornitore Tier-2: {e}")
            return False

    def get_component_materials(self, part_number: str) -> List[Dict[str, Any]]:
        """Restituisce i materiali custom associati a un Part Number."""
        df = self._load_sheet(SHEET_COMPONENT_MATERIALS)
        if df.empty:
            return []
        pn_normalized = self._normalize_pn(part_number)
        mask = df['Part_Number'].astype(str).str.upper() == pn_normalized
        return df[mask].to_dict('records')

    def add_component_material(self, part_number: str, material_data: Dict[str, Any]) -> bool:
        """Associa un materiale/fornitore Tier-2 a un Part Number."""
        try:
            df = self._load_sheet(SHEET_COMPONENT_MATERIALS)
            pn_normalized = self._normalize_pn(part_number)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            material_data['Part_Number'] = pn_normalized
            material_data['Created_at'] = now

            mat_key = material_data.get('Material_Key', '')

            if not df.empty:
                # Controlla se esiste gia'
                mask = (
                    (df['Part_Number'].astype(str).str.upper() == pn_normalized) &
                    (df['Material_Key'].astype(str).str.upper() == mat_key.upper())
                )
                if mask.any():
                    for col in df.columns:
                        if col in material_data and col != 'Created_at':
                            df.loc[mask, col] = material_data[col]
                    self._save_sheet(df, SHEET_COMPONENT_MATERIALS)
                    return True

            new_row = pd.DataFrame([material_data])
            df = pd.concat([df, new_row], ignore_index=True)
            self._save_sheet(df, SHEET_COMPONENT_MATERIALS)
            return True
        except Exception as e:
            print(f"Errore nell'associare materiale: {e}")
            return False

    def remove_component_material(self, part_number: str, material_key: str) -> bool:
        """Rimuove un'associazione materiale-componente."""
        try:
            df = self._load_sheet(SHEET_COMPONENT_MATERIALS)
            if df.empty:
                return False
            pn_normalized = self._normalize_pn(part_number)
            mask = (
                (df['Part_Number'].astype(str).str.upper() == pn_normalized) &
                (df['Material_Key'].astype(str).str.upper() == material_key.upper())
            )
            df = df[~mask]
            self._save_sheet(df, SHEET_COMPONENT_MATERIALS)
            return True
        except Exception as e:
            print(f"Errore nella rimozione materiale: {e}")
            return False

    def get_all_component_materials(self) -> Dict[str, List[Dict[str, Any]]]:
        """Restituisce tutte le associazioni, raggruppate per Part Number."""
        df = self._load_sheet(SHEET_COMPONENT_MATERIALS)
        if df.empty:
            return {}
        result = {}
        for _, row in df.iterrows():
            pn = str(row.get('Part_Number', '')).upper()
            if pn:
                if pn not in result:
                    result[pn] = []
                result[pn].append(row.to_dict())
        return result

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - STATISTICHE
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - EMS PROVIDERS (v4.0)
    # -------------------------------------------------------------------------

    def get_all_ems_providers(self) -> List[Dict[str, Any]]:
        """Restituisce tutti i fornitori EMS."""
        df = self._load_sheet(SHEET_EMS_PROVIDERS)
        if df.empty:
            return []
        return df.to_dict('records')

    def get_ems_provider(self, ems_name: str) -> Optional[Dict[str, Any]]:
        """Cerca un EMS provider per nome (case-insensitive)."""
        df = self._load_sheet(SHEET_EMS_PROVIDERS)
        if df.empty:
            return None
        mask = df['EMS_Name'].astype(str).str.upper() == ems_name.upper().strip()
        if mask.any():
            return df[mask].iloc[0].to_dict()
        return None

    def add_ems_provider(self, data: Dict[str, Any]) -> bool:
        """Aggiunge o aggiorna un fornitore EMS."""
        try:
            df = self._load_sheet(SHEET_EMS_PROVIDERS)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            ems_id = data.get('EMS_ID', '')
            if not ems_id:
                existing_ids = df['EMS_ID'].tolist() if not df.empty else []
                max_num = 0
                for eid in existing_ids:
                    try:
                        num = int(str(eid).replace('EMS_', ''))
                        max_num = max(max_num, num)
                    except (ValueError, TypeError):
                        pass
                ems_id = f"EMS_{max_num + 1:03d}"

            data['EMS_ID'] = ems_id
            data['Updated_at'] = now

            if df.empty:
                data['Created_at'] = now
                df = pd.DataFrame([data])
            else:
                mask = df['EMS_ID'].astype(str) == str(ems_id)
                if mask.any():
                    for col in df.columns:
                        if col in data and col != 'Created_at':
                            df.loc[mask, col] = data[col]
                else:
                    data['Created_at'] = now
                    new_row = pd.DataFrame([data])
                    df = pd.concat([df, new_row], ignore_index=True)

            self._save_sheet(df, SHEET_EMS_PROVIDERS)
            return True
        except Exception as e:
            print(f"Errore nell'aggiungere EMS provider: {e}")
            return False

    def remove_ems_provider(self, ems_id: str) -> bool:
        """Rimuove un fornitore EMS."""
        try:
            df = self._load_sheet(SHEET_EMS_PROVIDERS)
            if df.empty:
                return False
            mask = df['EMS_ID'].astype(str) == str(ems_id)
            df = df[~mask]
            self._save_sheet(df, SHEET_EMS_PROVIDERS)
            return True
        except Exception as e:
            print(f"Errore nella rimozione EMS provider: {e}")
            return False

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - DISTRIBUTORS (v4.0)
    # -------------------------------------------------------------------------

    def get_all_distributors(self) -> List[Dict[str, Any]]:
        """Restituisce tutti i distributori."""
        df = self._load_sheet(SHEET_DISTRIBUTORS)
        if df.empty:
            return []
        return df.to_dict('records')

    def get_distributor(self, distributor_id: str) -> Optional[Dict[str, Any]]:
        """Cerca un distributore per ID."""
        df = self._load_sheet(SHEET_DISTRIBUTORS)
        if df.empty:
            return None
        mask = df['Distributor_ID'].astype(str).str.upper() == distributor_id.upper()
        if mask.any():
            return df[mask].iloc[0].to_dict()
        return None

    def add_distributor(self, data: Dict[str, Any]) -> bool:
        """Aggiunge o aggiorna un distributore."""
        try:
            df = self._load_sheet(SHEET_DISTRIBUTORS)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            dist_id = data.get('Distributor_ID', '')
            if not dist_id:
                existing_ids = df['Distributor_ID'].tolist() if not df.empty else []
                max_num = 0
                for did in existing_ids:
                    try:
                        num = int(str(did).replace('DIST_', ''))
                        max_num = max(max_num, num)
                    except (ValueError, TypeError):
                        pass
                dist_id = f"DIST_{max_num + 1:03d}"

            data['Distributor_ID'] = dist_id
            data['Updated_at'] = now

            if df.empty:
                data['Created_at'] = now
                df = pd.DataFrame([data])
            else:
                mask = df['Distributor_ID'].astype(str) == str(dist_id)
                if mask.any():
                    for col in df.columns:
                        if col in data and col != 'Created_at':
                            df.loc[mask, col] = data[col]
                else:
                    data['Created_at'] = now
                    new_row = pd.DataFrame([data])
                    df = pd.concat([df, new_row], ignore_index=True)

            self._save_sheet(df, SHEET_DISTRIBUTORS)
            return True
        except Exception as e:
            print(f"Errore nell'aggiungere distributore: {e}")
            return False

    def remove_distributor(self, distributor_id: str) -> bool:
        """Rimuove un distributore."""
        try:
            df = self._load_sheet(SHEET_DISTRIBUTORS)
            if df.empty:
                return False
            mask = df['Distributor_ID'].astype(str) == str(distributor_id)
            df = df[~mask]
            self._save_sheet(df, SHEET_DISTRIBUTORS)
            return True
        except Exception as e:
            print(f"Errore nella rimozione distributore: {e}")
            return False

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - PART_DISTRIBUTORS (v4.0)
    # -------------------------------------------------------------------------

    def get_part_distributors(self, part_number: str) -> List[Dict[str, Any]]:
        """Restituisce i distributori associati a un Part Number."""
        df = self._load_sheet(SHEET_PART_DISTRIBUTORS)
        if df.empty:
            return []
        pn_norm = self._normalize_pn(part_number)
        mask = df['Part_Number'].astype(str).str.upper() == pn_norm
        rows = df[mask].to_dict('records')
        # Arricchisci con dati distributore
        result = []
        for row in rows:
            dist = self.get_distributor(str(row.get('Distributor_ID', '')))
            if dist:
                row['distributor_data'] = dist
            result.append(row)
        return result

    def add_part_distributor(self, part_number: str, data: Dict[str, Any]) -> bool:
        """Associa un distributore a un Part Number."""
        try:
            df = self._load_sheet(SHEET_PART_DISTRIBUTORS)
            pn_norm = self._normalize_pn(part_number)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            dist_id = str(data.get('Distributor_ID', ''))

            data['Part_Number'] = pn_norm
            data['Created_at'] = now

            if not df.empty:
                mask = (
                    (df['Part_Number'].astype(str).str.upper() == pn_norm) &
                    (df['Distributor_ID'].astype(str) == dist_id)
                )
                if mask.any():
                    for col in df.columns:
                        if col in data and col != 'Created_at':
                            df.loc[mask, col] = data[col]
                    self._save_sheet(df, SHEET_PART_DISTRIBUTORS)
                    return True

            new_row = pd.DataFrame([data])
            df = pd.concat([df, new_row], ignore_index=True)
            self._save_sheet(df, SHEET_PART_DISTRIBUTORS)
            return True
        except Exception as e:
            print(f"Errore nell'associare distributore: {e}")
            return False

    def remove_part_distributor(self, part_number: str, distributor_id: str) -> bool:
        """Rimuove un'associazione PN-distributore."""
        try:
            df = self._load_sheet(SHEET_PART_DISTRIBUTORS)
            if df.empty:
                return False
            pn_norm = self._normalize_pn(part_number)
            mask = (
                (df['Part_Number'].astype(str).str.upper() == pn_norm) &
                (df['Distributor_ID'].astype(str) == str(distributor_id))
            )
            df = df[~mask]
            self._save_sheet(df, SHEET_PART_DISTRIBUTORS)
            return True
        except Exception as e:
            print(f"Errore nella rimozione associazione PN-distributore: {e}")
            return False

    def get_all_part_distributors(self) -> Dict[str, List[Dict[str, Any]]]:
        """Restituisce tutte le associazioni PN→distributori."""
        df = self._load_sheet(SHEET_PART_DISTRIBUTORS)
        if df.empty:
            return {}
        result = {}
        for _, row in df.iterrows():
            pn = str(row.get('Part_Number', '')).upper()
            if pn:
                if pn not in result:
                    result[pn] = []
                dist = self.get_distributor(str(row.get('Distributor_ID', '')))
                row_dict = row.to_dict()
                if dist:
                    row_dict['distributor_data'] = dist
                result[pn].append(row_dict)
        return result

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - ALT_SOURCES (v4.0)
    # -------------------------------------------------------------------------

    def get_alt_sources(self, part_number: str) -> List[Dict[str, Any]]:
        """Restituisce le fonti alternative per un Part Number."""
        df = self._load_sheet(SHEET_ALT_SOURCES)
        if df.empty:
            return []
        pn_norm = self._normalize_pn(part_number)
        mask = df['Part_Number'].astype(str).str.upper() == pn_norm
        return df[mask].to_dict('records')

    def get_all_alt_sources(self) -> Dict[str, List[Dict[str, Any]]]:
        """Restituisce tutte le fonti alternative, raggruppate per PN."""
        df = self._load_sheet(SHEET_ALT_SOURCES)
        if df.empty:
            return {}
        result = {}
        for _, row in df.iterrows():
            pn = str(row.get('Part_Number', '')).upper()
            if pn:
                if pn not in result:
                    result[pn] = []
                result[pn].append(row.to_dict())
        return result

    def add_alt_source(self, part_number: str, data: Dict[str, Any]) -> bool:
        """Aggiunge una fonte alternativa per un Part Number."""
        try:
            df = self._load_sheet(SHEET_ALT_SOURCES)
            pn_norm = self._normalize_pn(part_number)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            supplier = str(data.get('Supplier_Name', '')).strip()

            data['Part_Number'] = pn_norm
            data['Created_at'] = now

            if not df.empty:
                mask = (
                    (df['Part_Number'].astype(str).str.upper() == pn_norm) &
                    (df['Supplier_Name'].astype(str).str.upper() == supplier.upper())
                )
                if mask.any():
                    for col in df.columns:
                        if col in data and col != 'Created_at':
                            df.loc[mask, col] = data[col]
                    self._save_sheet(df, SHEET_ALT_SOURCES)
                    return True

            new_row = pd.DataFrame([data])
            df = pd.concat([df, new_row], ignore_index=True)
            self._save_sheet(df, SHEET_ALT_SOURCES)
            return True
        except Exception as e:
            print(f"Errore nell'aggiungere fonte alternativa: {e}")
            return False

    def remove_alt_source(self, part_number: str, supplier_name: str) -> bool:
        """Rimuove una fonte alternativa."""
        try:
            df = self._load_sheet(SHEET_ALT_SOURCES)
            if df.empty:
                return False
            pn_norm = self._normalize_pn(part_number)
            mask = (
                (df['Part_Number'].astype(str).str.upper() == pn_norm) &
                (df['Supplier_Name'].astype(str).str.upper() == supplier_name.upper())
            )
            df = df[~mask]
            self._save_sheet(df, SHEET_ALT_SOURCES)
            return True
        except Exception as e:
            print(f"Errore nella rimozione fonte alternativa: {e}")
            return False

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - SUPPLIER_PROFILES (v4.0)
    # -------------------------------------------------------------------------

    def get_all_supplier_profiles(self) -> List[Dict[str, Any]]:
        """Restituisce tutti i profili fornitore."""
        df = self._load_sheet(SHEET_SUPPLIER_PROFILES)
        if df.empty:
            return []
        return df.to_dict('records')

    def get_supplier_profile(self, supplier_name: str) -> Optional[Dict[str, Any]]:
        """Cerca il profilo di un fornitore per nome."""
        df = self._load_sheet(SHEET_SUPPLIER_PROFILES)
        if df.empty:
            return None
        mask = df['Supplier_Name'].astype(str).str.upper() == supplier_name.upper().strip()
        if mask.any():
            return df[mask].iloc[0].to_dict()
        return None

    def add_supplier_profile(self, data: Dict[str, Any]) -> bool:
        """Aggiunge o aggiorna un profilo fornitore."""
        try:
            df = self._load_sheet(SHEET_SUPPLIER_PROFILES)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            supplier_id = data.get('Supplier_ID', '')
            supplier_name = str(data.get('Supplier_Name', '')).strip()

            if not supplier_id and supplier_name:
                # Auto-genera ID dal nome
                supplier_id = 'SUP_' + supplier_name.upper().replace(' ', '_')[:10]

            data['Supplier_ID'] = supplier_id
            data['Updated_at'] = now

            if df.empty:
                data['Created_at'] = now
                df = pd.DataFrame([data])
            else:
                mask = df['Supplier_Name'].astype(str).str.upper() == supplier_name.upper()
                if mask.any():
                    for col in df.columns:
                        if col in data and col != 'Created_at':
                            df.loc[mask, col] = data[col]
                else:
                    data['Created_at'] = now
                    new_row = pd.DataFrame([data])
                    df = pd.concat([df, new_row], ignore_index=True)

            self._save_sheet(df, SHEET_SUPPLIER_PROFILES)
            return True
        except Exception as e:
            print(f"Errore nell'aggiungere profilo fornitore: {e}")
            return False

    def remove_supplier_profile(self, supplier_name: str) -> bool:
        """Rimuove un profilo fornitore."""
        try:
            df = self._load_sheet(SHEET_SUPPLIER_PROFILES)
            if df.empty:
                return False
            mask = df['Supplier_Name'].astype(str).str.upper() == supplier_name.upper()
            df = df[~mask]
            self._save_sheet(df, SHEET_SUPPLIER_PROFILES)
            return True
        except Exception as e:
            print(f"Errore nella rimozione profilo fornitore: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche sul database."""
        stats = {
            'total_part_numbers': 0,
            'total_clients': 0,
            'total_client_records': 0,
            'categories': {},
            'suppliers': {}
        }

        # Part numbers
        df_pn = self._load_sheet(SHEET_PART_NUMBERS)
        if not df_pn.empty:
            stats['total_part_numbers'] = len(df_pn['Part Number'].dropna().unique())

            # Categorie
            cat_col = 'Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)'
            if cat_col in df_pn.columns:
                stats['categories'] = df_pn[cat_col].value_counts().to_dict()

            # Fornitori
            if 'Supplier Name' in df_pn.columns:
                stats['suppliers'] = df_pn['Supplier Name'].value_counts().to_dict()

        # Clienti
        df_clients = self._load_sheet(SHEET_CLIENTS)
        if not df_clients.empty:
            stats['total_clients'] = len(df_clients)

        # Record cliente
        df_client_data = self._load_sheet(SHEET_CLIENT_DATA)
        if not df_client_data.empty:
            stats['total_client_records'] = len(df_client_data)

        # Tier-2 Suppliers
        df_t2 = self._load_sheet(SHEET_TIER2_SUPPLIERS)
        stats['total_tier2_suppliers'] = len(df_t2) if not df_t2.empty else 0

        # v4.0 - Filiera commerciale
        df_ems = self._load_sheet(SHEET_EMS_PROVIDERS)
        stats['total_ems_providers'] = len(df_ems) if not df_ems.empty else 0

        df_dist = self._load_sheet(SHEET_DISTRIBUTORS)
        stats['total_distributors'] = len(df_dist) if not df_dist.empty else 0

        df_alt = self._load_sheet(SHEET_ALT_SOURCES)
        stats['total_alt_sources'] = len(df_alt) if not df_alt.empty else 0

        df_sup = self._load_sheet(SHEET_SUPPLIER_PROFILES)
        stats['total_supplier_profiles'] = len(df_sup) if not df_sup.empty else 0

        return stats
