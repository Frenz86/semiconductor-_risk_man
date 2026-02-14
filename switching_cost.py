"""
Switching Cost Calculator
=========================
Modulo per la stima del costo temporale ed economico di sostituzione
di un componente elettronico, basato su:
- Dimensione del codice SW/firmware
- Tipo di OS (Linux/RTOS/Baremetal)
- Certificazioni richieste
- Tempo di qualifica

Uso:
    from switching_cost import calculate_switching_cost, estimate_redesign_risk
"""

import pandas as pd
from typing import Dict, Any, Optional


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

# Ore-uomo per KB di codice, per tipo di OS
SW_PORTING_RATES = {
    'baremetal': 0.5,   # Porting driver/HAL semplice
    'bare metal': 0.5,
    'rtos': 1.0,        # BSP + driver RTOS
    'freertos': 1.0,
    'zephyr': 1.0,
    'linux': 2.0,        # Kernel, BSP, device tree, driver framework
    'android': 2.5,      # Linux + HAL Android
    'windows': 1.5,      # Driver model Windows
}

# Moltiplicatori per tipo di certificazione
CERTIFICATION_MULTIPLIERS = {
    'aec-q100': 1.5,      # Automotive
    'aec-q101': 1.5,
    'aec-q200': 1.3,
    'automotive': 1.5,
    'mil-std': 2.0,        # Military
    'mil-prf': 2.0,
    'military': 2.0,
    'iec 62443': 1.3,      # Cybersecurity
    'iec 61508': 1.4,      # Safety
    'iso 26262': 1.5,      # Automotive functional safety
    'do-254': 1.8,         # Avionics
    'do-178': 1.8,
    'medical': 1.6,        # IEC 62304
    'iec 62304': 1.6,
    'ce': 1.0,
    'ul': 1.1,
    'rohs': 1.0,
}

# Soglie di classificazione redesign
REDESIGN_THRESHOLDS = [
    {'max_hours': 100, 'classification': 'TRIVIALE', 'color': 'GREEN',
     'description': 'Componente facilmente sostituibile'},
    {'max_hours': 500, 'classification': 'MODERATO', 'color': 'YELLOW',
     'description': 'Sostituzione richiede pianificazione'},
    {'max_hours': 2000, 'classification': 'COMPLESSO', 'color': 'ORANGE',
     'description': 'Sostituzione richiede progetto dedicato'},
    {'max_hours': float('inf'), 'classification': 'CRITICO', 'color': 'RED',
     'description': 'Sostituzione equivale a redesign completo'},
]

# Ore-uomo per settimana di qualifica
HOURS_PER_QUAL_WEEK = 40


# =============================================================================
# FUNZIONI
# =============================================================================

def _get_safe(row: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Ottiene un valore in modo sicuro."""
    val = row.get(key, default)
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    return val


def _parse_certification_multiplier(certification: str) -> float:
    """Trova il moltiplicatore massimo tra le certificazioni elencate."""
    if not certification:
        return 1.0

    cert_lower = str(certification).lower()
    max_mult = 1.0

    for cert_key, mult in CERTIFICATION_MULTIPLIERS.items():
        if cert_key in cert_lower:
            max_mult = max(max_mult, mult)

    return max_mult


def calculate_switching_cost(component: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcola il costo stimato di sostituzione di un componente.

    Args:
        component: Dizionario con dati del componente. Usa:
            - SW_Code_Size_KB (o 'Size of SW / Firmware Code...')
            - OS_Type (o 'OS or Baremetal')
            - Weeks to qualify
            - Specify Certification/Qualification
            - Supplier Lead Time (weeks)

    Returns:
        Dizionario con:
            - sw_porting_hours: ore per porting software
            - qualification_hours: ore per qualifica
            - certification_multiplier: moltiplicatore certificazione
            - total_switching_hours: totale ore-uomo
            - classification: TRIVIALE/MODERATO/COMPLESSO/CRITICO
            - breakdown: dettaglio dei costi
    """
    # --- SW Porting ---
    sw_size = _get_safe(component, 'SW_Code_Size_KB', 0)
    if not sw_size:
        # Fallback: cerca colonna originale BOM
        sw_size = _get_safe(component, 'Size of SW / Firmware Code that runs on this Part Number (KB)', 0)
    try:
        sw_size = float(sw_size) if sw_size else 0
    except (ValueError, TypeError):
        sw_size = 0

    os_type = str(_get_safe(component, 'OS_Type', '') or
                  _get_safe(component, 'OS or Baremetal', '') or '').strip().lower()

    # Trova rate di porting
    porting_rate = 0
    for os_key, rate in SW_PORTING_RATES.items():
        if os_key in os_type:
            porting_rate = rate
            break

    # Se non riconosciuto ma c'e' codice, assume baremetal
    if porting_rate == 0 and sw_size > 0:
        porting_rate = SW_PORTING_RATES['baremetal']

    sw_porting_hours = sw_size * porting_rate

    # --- Qualification Time ---
    weeks_qualify = _get_safe(component, 'Weeks to qualify', 0)
    try:
        weeks_qualify = float(weeks_qualify) if weeks_qualify else 0
    except (ValueError, TypeError):
        weeks_qualify = 0

    qualification_hours = weeks_qualify * HOURS_PER_QUAL_WEEK

    # --- Certification Multiplier ---
    certification = str(_get_safe(component, 'Specify Certification/Qualification', '') or '')
    cert_multiplier = _parse_certification_multiplier(certification)

    # --- Total ---
    base_hours = sw_porting_hours + qualification_hours
    total_hours = base_hours * cert_multiplier

    # --- Classification ---
    classification = 'TRIVIALE'
    color = 'GREEN'
    description = ''
    for threshold in REDESIGN_THRESHOLDS:
        if total_hours <= threshold['max_hours']:
            classification = threshold['classification']
            color = threshold['color']
            description = threshold['description']
            break

    # Breakdown dettagliato
    breakdown = []
    if sw_porting_hours > 0:
        os_label = os_type.title() if os_type else 'N/A'
        breakdown.append({
            'item': f'SW Porting ({os_label}, {sw_size:.0f} KB)',
            'hours': round(sw_porting_hours, 1),
        })
    if qualification_hours > 0:
        breakdown.append({
            'item': f'Qualifica ({weeks_qualify:.0f} settimane)',
            'hours': round(qualification_hours, 1),
        })
    if cert_multiplier > 1.0:
        overhead = total_hours - base_hours
        breakdown.append({
            'item': f'Overhead Certificazione ({certification}, x{cert_multiplier})',
            'hours': round(overhead, 1),
        })

    # Se nessun dato SW, stima minima basata su categoria
    if total_hours == 0:
        category = str(_get_safe(component, 'Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)', '') or '').lower()
        proprietary = str(_get_safe(component, 'Proprietary (Y/N)**', 'N') or '').upper()

        if proprietary == 'Y':
            total_hours = 200
            classification = 'MODERATO'
            color = 'YELLOW'
            description = 'Componente proprietario (stima minima)'
            breakdown.append({'item': 'Stima minima (proprietario)', 'hours': 200})
        elif 'mcu' in category or 'mpu' in category:
            total_hours = 80
            classification = 'TRIVIALE'
            color = 'GREEN'
            description = 'Stima minima per processore'
            breakdown.append({'item': 'Stima minima (processore)', 'hours': 80})
        elif 'passive' in category or 'connector' in category:
            total_hours = 8
            classification = 'TRIVIALE'
            color = 'GREEN'
            description = 'Componente passivo/connettore'
            breakdown.append({'item': 'Sostituzione diretta', 'hours': 8})

    return {
        'sw_porting_hours': round(sw_porting_hours, 1),
        'qualification_hours': round(qualification_hours, 1),
        'certification_multiplier': cert_multiplier,
        'certification_name': certification if certification else 'Nessuna',
        'total_switching_hours': round(total_hours, 1),
        'classification': classification,
        'color': color,
        'description': description,
        'breakdown': breakdown,
        'os_type': os_type.title() if os_type else 'N/A',
        'sw_size_kb': sw_size,
    }


def estimate_redesign_risk(component: Dict[str, Any]) -> str:
    """
    Restituisce la classificazione del rischio di redesign.

    Returns:
        'TRIVIALE', 'MODERATO', 'COMPLESSO', o 'CRITICO'
    """
    result = calculate_switching_cost(component)
    return result['classification']
