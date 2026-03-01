"""
alternative_engine.py — Compatibility Graph + Alternative Suggestion Engine (v5.0)

Dato un componente ad alto rischio e le sue fonti alternative (Alt_Sources),
calcola un compatibility score per ciascuna alternativa tenendo conto di:
  - Compatibilità interfaccia (DDR3/DDR4/DDR5/LPDDR4/LPDDR5/...)
  - Disponibilità di mercato (Market_Shortage)
  - Package compatibility
  - Effort di porting stimato
"""

from typing import Dict, List, Any, Optional

# Severity → penalità disponibilità (0.0 = nessuna, 1.0 = inutilizzabile)
_SEVERITY_PENALTY = {
    'Available': 0.0,
    'Tight':     0.2,
    'Shortage':  0.6,
    'Critical':  0.9,
    'EOL':       1.0,
}

# Massimo ore porting usato per normalizzazione (sopra questo = effort massimo)
_MAX_PORTING_HOURS = 500

# Interfacce raggruppate per famiglia (compatibilità parziale intra-famiglia)
_INTERFACE_FAMILIES = {
    'DDR': ['DDR3', 'DDR3L', 'DDR4', 'DDR5'],
    'LPDDR': ['LPDDR3', 'LPDDR4', 'LPDDR4X', 'LPDDR5', 'LPDDR5X'],
    'FLASH': ['NOR_Flash', 'NAND_Flash', 'SPI_Flash', 'QSPI_Flash'],
    'SRAM': ['SRAM', 'PSRAM', 'HyperRAM'],
}


def _parse_interfaces(interface_str: str) -> List[str]:
    """Parsa una stringa di interfacce CSV in lista normalizzata."""
    if not interface_str or str(interface_str).strip() in ('', 'nan', 'None'):
        return []
    return [i.strip().upper() for i in str(interface_str).split(',') if i.strip()]


def _same_family(iface_a: str, iface_b: str) -> bool:
    """True se le due interfacce appartengono alla stessa famiglia (es. DDR4 e DDR5)."""
    a = iface_a.upper()
    b = iface_b.upper()
    for family in _INTERFACE_FAMILIES.values():
        family_upper = [f.upper() for f in family]
        if a in family_upper and b in family_upper:
            return True
    return False


def _check_interface_compatibility(
    pn_supported: str,
    alt_interface: str,
) -> tuple:
    """
    Verifica se l'alternativa è compatibile con le interfacce supportate dal PN.

    Returns:
        (compatible: bool, same_family: bool)
        - compatible=True  → interfaccia esatta supportata dal processore
        - same_family=True → stessa famiglia (es. DDR4 invece di DDR5), porting possibile
    """
    if not alt_interface or not pn_supported:
        return False, False

    supported = _parse_interfaces(pn_supported)
    alt = alt_interface.strip().upper()

    if not supported:
        return False, False

    if alt in supported:
        return True, True

    # Stessa famiglia → compatibile con porting
    for sup in supported:
        if _same_family(sup, alt):
            return False, True

    return False, False


def score_alternative(
    pn_data: Dict[str, Any],
    alt: Dict[str, Any],
    market_shortage: Dict[str, str],
) -> float:
    """
    Calcola un compatibility score composito (0.0–1.0) per un'alternativa.

    Pesi:
      0.40 — interface match (esatto = 1.0, stessa famiglia = 0.5, nessuno = 0.0)
      0.30 — availability (penalizza Shortage/Critical)
      0.20 — package compatibility (Y=1.0, Partial=0.5, N=0.0)
      0.10 — porting effort (0 ore = 1.0, _MAX_PORTING_HOURS+ = 0.0)
    """
    score = 0.0

    # --- Interface match (0.40) ---
    pn_interfaces = str(pn_data.get('Supported_Interfaces', ''))
    alt_interface = str(alt.get('Interface_Type', ''))
    exact_match, family_match = _check_interface_compatibility(pn_interfaces, alt_interface)

    if exact_match:
        score += 0.40
    elif family_match:
        score += 0.20
    elif not alt_interface or alt_interface in ('', 'nan'):
        # Interfaccia non specificata → non penalizzare completamente
        score += 0.15

    # --- Availability (0.30) ---
    alt_avail = str(alt.get('Availability_Status', 'Available')).strip()
    # Controlla anche il market shortage globale per questa interfaccia
    global_severity = market_shortage.get(alt_interface.upper(), 'Available')
    worst_severity = _pick_worst_severity(alt_avail, global_severity)
    penalty = _SEVERITY_PENALTY.get(worst_severity, 0.0)
    score += 0.30 * (1.0 - penalty)

    # --- Package compatibility (0.20) ---
    pkg = str(alt.get('Package_Compatible', '')).strip().upper()
    if pkg == 'Y':
        score += 0.20
    elif pkg == 'PARTIAL':
        score += 0.10

    # --- Porting effort (0.10) ---
    try:
        hours = float(alt.get('Porting_Effort_Hours', 0) or 0)
        effort_score = max(0.0, 1.0 - hours / _MAX_PORTING_HOURS)
        score += 0.10 * effort_score
    except (ValueError, TypeError):
        score += 0.05  # dati mancanti → medio

    return round(min(score, 1.0), 3)


def _pick_worst_severity(a: str, b: str) -> str:
    """Restituisce la severity peggiore tra due."""
    order = ['Available', 'Tight', 'Shortage', 'Critical', 'EOL']
    ia = order.index(a) if a in order else 0
    ib = order.index(b) if b in order else 0
    return order[max(ia, ib)]


def find_compatible_alternatives(
    pn: str,
    pn_data: Dict[str, Any],
    alt_sources: List[Dict[str, Any]],
    market_shortage: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Dato un PN e le sue fonti alternative, restituisce la lista ordinata per
    compatibility score (discendente).

    Ogni elemento restituito:
    {
        'supplier':        str,
        'compat_score':    float,   # 0.0–1.0
        'interface_type':  str,
        'interface_exact': bool,
        'interface_family':bool,
        'drop_in':         str,     # Y / N / Partial
        'porting_hours':   int,
        'availability':    str,     # da Alt_Sources
        'market_severity': str,     # da Market_Shortage globale
        'package_compat':  str,
        'qualification':   str,
        'lead_time_weeks': Any,
        'frontend_country':str,
        'notes':           str,
    }
    """
    if not alt_sources:
        return []

    pn_interfaces = str(pn_data.get('Supported_Interfaces', ''))
    results = []

    for alt in alt_sources:
        alt_interface = str(alt.get('Interface_Type', '')).strip()
        exact, family = _check_interface_compatibility(pn_interfaces, alt_interface)
        global_severity = market_shortage.get(alt_interface.upper(), 'Available')

        results.append({
            'supplier':         str(alt.get('Supplier_Name', '')),
            'compat_score':     score_alternative(pn_data, alt, market_shortage),
            'interface_type':   alt_interface,
            'interface_exact':  exact,
            'interface_family': family,
            'drop_in':          str(alt.get('Drop_In_Replacement', '')),
            'porting_hours':    _safe_int(alt.get('Porting_Effort_Hours')),
            'availability':     str(alt.get('Availability_Status', '')),
            'market_severity':  global_severity,
            'package_compat':   str(alt.get('Package_Compatible', '')),
            'qualification':    str(alt.get('Qualification_Status', '')),
            'lead_time_weeks':  alt.get('Lead_Time_Weeks'),
            'frontend_country': str(alt.get('Frontend_Country', '')),
            'notes':            str(alt.get('Notes', '')),
        })

    results.sort(key=lambda x: x['compat_score'], reverse=True)
    return results


def check_shortage_impact(
    pn_data: Dict[str, Any],
    market_shortage: Dict[str, str],
) -> Dict[str, Any]:
    """
    Verifica se il PN è impattato da uno shortage di mercato in base alle sue
    interfacce supportate.

    Returns:
    {
        'affected': bool,
        'severity': str,          # worst severity trovata
        'affected_interfaces': list[str],
        'shortage_notes': list[str],
    }
    """
    if not market_shortage:
        return {'affected': False, 'severity': 'Available', 'affected_interfaces': [], 'shortage_notes': []}

    pn_interfaces = _parse_interfaces(str(pn_data.get('Supported_Interfaces', '')))
    # Considera anche Memory_Type (campo legacy)
    memory_type = str(pn_data.get('Memory_Type', '')).strip()
    if memory_type and memory_type not in ('', 'nan', 'None'):
        pn_interfaces.append(memory_type.upper())

    affected = []
    notes = []
    worst = 'Available'

    for iface in pn_interfaces:
        severity = market_shortage.get(iface, None)
        if severity and severity != 'Available':
            affected.append(iface)
            worst = _pick_worst_severity(worst, severity)

    # Controlla anche per famiglia (es. PN supporta DDR4, shortage su LPDDR4)
    for shortage_iface, severity in market_shortage.items():
        if severity in ('Shortage', 'Critical') and shortage_iface not in affected:
            for pn_iface in pn_interfaces:
                if _same_family(pn_iface, shortage_iface):
                    notes.append(f"{shortage_iface} ({severity}) — same family as {pn_iface}")

    return {
        'affected': len(affected) > 0,
        'severity': worst,
        'affected_interfaces': affected,
        'shortage_notes': notes,
    }


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(float(val)) if val is not None and str(val) not in ('', 'nan') else default
    except (ValueError, TypeError):
        return default
