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

DEFAULT_DB_NAME = 'part_numbers_db.xlsx'

# Nomi dei fogli Excel
SHEET_PART_NUMBERS = 'Part_Numbers'
SHEET_CLIENT_DATA = 'Client_Data'
SHEET_CLIENTS = 'Clients'

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
            # Foglio Part_Numbers
            pd.DataFrame(columns=PART_NUMBERS_COLUMNS).to_excel(
                writer, sheet_name=SHEET_PART_NUMBERS, index=False
            )
            # Foglio Client_Data
            pd.DataFrame(columns=CLIENT_DATA_COLUMNS).to_excel(
                writer, sheet_name=SHEET_CLIENT_DATA, index=False
            )
            # Foglio Clients
            pd.DataFrame(columns=CLIENTS_COLUMNS).to_excel(
                writer, sheet_name=SHEET_CLIENTS, index=False
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

            return True
        except Exception as e:
            print(f"Errore nella migrazione del database: {e}")
            return False

    # -------------------------------------------------------------------------
    # METODI PUBBLICI - STATISTICHE
    # -------------------------------------------------------------------------

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

        return stats
