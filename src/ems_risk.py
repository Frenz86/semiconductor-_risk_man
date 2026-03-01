"""
EMS Risk Scoring Module - v4.0
===============================
Modulo per il calcolo del rischio EMS (Electronics Manufacturing Services).

Valuta il rischio del terzista/EMS in base a:
- Salute finanziaria
- Utilizzo capacità produttiva
- Numero siti di backup
- Concentrazione geografica
- Gap certificazioni

Uso:
    from ems_risk import calculate_ems_risk
    result = calculate_ems_risk(component_data, ems_provider_data)
"""

import pandas as pd
from typing import Dict, Any, Optional


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

# Punteggio per salute finanziaria EMS
EMS_FINANCIAL_SCORES = {
    'A': 0,
    'B': 3,
    'C': 8,
    'D': 15,
}

# Punteggio per utilizzo capacità (%)
# Alta utilization = rischio di overflow e ritardi
EMS_CAPACITY_THRESHOLDS = [
    (95, 15, 'CRITICAL: EMS at full capacity (>95%) - high risk of delays'),
    (85, 8,  'HIGH: EMS nearly saturated (>85%)'),
    (70, 3,  'MEDIUM: EMS at good capacity (>70%)'),
    (0,  0,  ''),
]

# Punteggio per numero siti di backup
EMS_BACKUP_SCORES = {
    0: 12,  # Nessun sito alternativo
    1: 6,   # Un solo sito alternativo
    2: 2,   # Due siti alternativi
}
EMS_BACKUP_GOOD_THRESHOLD = 3  # >= 3 siti: bonus -2

# Paesi ad alto rischio per EMS (stesso schema di geo_risk)
EMS_COUNTRY_RISK = {
    'china': 15,
    'taiwan': 12,
    'korea': 8,
    'japan': 6,
    'malaysia': 5,
    'philippines': 5,
    'vietnam': 4,
    'thailand': 4,
    'singapore': 3,
    'india': 3,
    'mexico': 2,
    'usa': 0,
    'germany': 0,
    'uk': 0,
    'france': 0,
    'italy': 0,
    'netherlands': 0,
}

# Certificazioni rilevanti e loro "peso" nel valutare il gap
CERTIFICATION_WEIGHTS = {
    'ISO9001': 1,
    'IATF16949': 3,   # Automotive - critico
    'AS9100': 3,      # Aerospace - critico
    'ISO13485': 2,    # Medical
    'IPC-J-STD-001': 1,
    'IPC-A-610': 1,
}


# =============================================================================
# FUNZIONI DI UTILITÀ
# =============================================================================

def _safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Ottiene un valore in modo sicuro gestendo NaN."""
    val = data.get(key, default)
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    return val


def _parse_certifications(cert_string: str) -> set:
    """Parsa una stringa di certificazioni comma-separated."""
    if not cert_string or not isinstance(cert_string, str):
        return set()
    return {c.strip().upper() for c in cert_string.split(',') if c.strip()}


# =============================================================================
# CALCOLO RISCHIO EMS
# =============================================================================

def calculate_ems_risk(
    component_data: Dict[str, Any],
    ems_provider_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calcola il rischio EMS per un componente.

    Se EMS_Used != 'Y' o non c'è profilo EMS, restituisce score 0.

    Args:
        component_data: Dati del componente dal database
        ems_provider_data: Profilo EMS da EMS_Providers sheet (opzionale)

    Returns:
        {
            'ems_score': int (0-30),
            'ems_used': bool,
            'ems_name': str,
            'ems_country': str,
            'has_profile': bool,
            'factors': List[str],
            'suggestions': List[str],
            'breakdown': List[Dict],
        }
    """
    ems_used = str(_safe_get(component_data, 'EMS_Used', 'N')).strip().upper()

    if ems_used != 'Y':
        return {
            'ems_score': 0,
            'ems_used': False,
            'ems_name': '',
            'ems_country': '',
            'has_profile': False,
            'factors': [],
            'suggestions': [],
            'breakdown': [],
        }

    ems_name = str(_safe_get(component_data, 'EMS_Name', '') or '').strip()
    ems_location = str(_safe_get(component_data, 'EMS_Location', '') or '').strip()

    # Se non c'è profilo dettagliato, usa solo la location per il geo risk
    if not ems_provider_data:
        geo_score = _calc_geo_score(ems_location)
        factors = []
        suggestions = []
        if geo_score > 0:
            factors.append(f"🏭 EMS in {ems_location.title()} (detailed profile not available)")
            suggestions.append(f"Add EMS profile '{ems_name}' in Database Management → EMS Providers")

        return {
            'ems_score': min(30, geo_score),
            'ems_used': True,
            'ems_name': ems_name,
            'ems_country': ems_location,
            'has_profile': False,
            'factors': factors,
            'suggestions': suggestions,
            'breakdown': [{'factor': 'Geo (estimate from location)', 'score': geo_score}],
        }

    # =========================================================================
    # CALCOLO COMPLETO CON PROFILO EMS
    # =========================================================================
    score = 0
    factors = []
    suggestions = []
    breakdown = []

    ems_country = str(_safe_get(ems_provider_data, 'Country', ems_location) or ems_location).strip()

    # 1. SALUTE FINANZIARIA (max 15 punti)
    fin_health = str(_safe_get(ems_provider_data, 'Financial_Health', 'B') or 'B').strip().upper()
    fin_score = EMS_FINANCIAL_SCORES.get(fin_health, 3)
    score += fin_score
    breakdown.append({'factor': f'Financial Health ({fin_health})', 'score': fin_score})
    if fin_score >= 8:
        factors.append(f"💰 HIGH: EMS financial health rating {fin_health}")
        suggestions.append("Evaluate an alternative EMS with a higher financial rating")
    elif fin_score >= 3:
        factors.append(f"💰 MEDIUM: EMS financial health rating {fin_health}")

    # 2. UTILIZZO CAPACITÀ (max 15 punti)
    capacity = _safe_get(ems_provider_data, 'Capacity_Utilization_Pct', 70)
    try:
        capacity_f = float(capacity) if capacity is not None else 70
    except (ValueError, TypeError):
        capacity_f = 70

    cap_score = 0
    cap_label = ''
    for threshold, pts, label in EMS_CAPACITY_THRESHOLDS:
        if capacity_f > threshold:
            cap_score = pts
            cap_label = label
            break
    score += cap_score
    breakdown.append({'factor': f'Capacity Utilization ({capacity_f:.0f}%)', 'score': cap_score})
    if cap_label:
        factors.append(f"⚙️ {cap_label}")
        if cap_score >= 8:
            suggestions.append("Negotiate dedicated capacity or qualify an alternative EMS")

    # 3. SITI DI BACKUP (max 12 punti)
    backup_sites = _safe_get(ems_provider_data, 'Backup_Sites_Count', 0)
    try:
        backup_n = int(float(backup_sites)) if backup_sites is not None else 0
    except (ValueError, TypeError):
        backup_n = 0

    if backup_n >= EMS_BACKUP_GOOD_THRESHOLD:
        backup_score = -2  # Bonus: good resilience
        factors.append(f"✅ MITIGATED: EMS has {backup_n} backup sites (-2 pts)")
    else:
        backup_score = EMS_BACKUP_SCORES.get(min(backup_n, 2), 2)
        if backup_score >= 12:
            factors.append("🏭 CRITICAL: EMS with no backup sites (single-site)")
            suggestions.append("Request business continuity agreement or qualify a second EMS")
        elif backup_score >= 6:
            factors.append(f"🏭 HIGH: EMS with only {backup_n} backup site")

    score += backup_score
    breakdown.append({'factor': f'Backup Sites ({backup_n})', 'score': backup_score})

    # 4. CONCENTRAZIONE GEOGRAFICA (max 15 punti)
    geo_score = _calc_geo_score(ems_country)

    # Bonus: se EMS è in paese diverso dal frontend del componente → rischio cumulato
    frontend = str(_safe_get(component_data, 'Frontend_Country', '') or '').lower().strip()
    if frontend and ems_country.lower().strip() == frontend:
        geo_score += 5
        factors.append(f"🌏 HIGH: EMS in the same country as Frontend ({ems_country.title()}) - geographic concentration")
        suggestions.append("Consider EMS in a different country for geographic diversification")
    elif geo_score > 0:
        factors.append(f"🌏 MEDIUM: EMS in {ems_country.title()} - moderate geo risk")

    score += geo_score
    breakdown.append({'factor': f'Geo Risk ({ems_country.title()})', 'score': geo_score})

    # 5. GAP CERTIFICAZIONI (max 10 punti)
    ems_certs = _parse_certifications(str(_safe_get(ems_provider_data, 'Certifications', '') or ''))
    component_auto_grade = str(_safe_get(component_data, 'Automotive_Grade', '') or '').strip()

    cert_gap_score = 0
    if component_auto_grade and component_auto_grade.upper() not in ('', 'NONE', 'N/A'):
        if 'IATF16949' not in ems_certs and 'IATF' not in ' '.join(ems_certs):
            cert_gap_score += 8
            factors.append("📋 CRITICAL: Automotive component but EMS not IATF16949 certified")
            suggestions.append("Request IATF16949 certification from EMS or qualify an automotive-certified EMS")

    if 'ISO9001' not in ems_certs and not any('ISO9001' in c for c in ems_certs):
        cert_gap_score += 3
        factors.append("📋 MEDIUM: EMS lacking basic ISO9001 certification")
        suggestions.append("Verify EMS quality management system")

    score += cert_gap_score
    breakdown.append({'factor': 'Certification Gap', 'score': cert_gap_score})

    # 6. ANNI DI ATTIVITÀ (informativo, piccola penalità se giovane)
    years = _safe_get(ems_provider_data, 'Years_Business', 10)
    try:
        years_n = int(float(years)) if years is not None else 10
    except (ValueError, TypeError):
        years_n = 10

    if years_n < 5:
        score += 5
        factors.append(f"🏢 MEDIUM: EMS with only {years_n} years in business - limited track record")
    elif years_n >= 20:
        score = max(0, score - 1)  # Piccolo bonus per EMS storico

    breakdown.append({'factor': f'Years in Business ({years_n})', 'score': 5 if years_n < 5 else 0})

    # Cap a 30 punti
    score = max(0, min(30, score))

    # Classification
    if score >= 20:
        level = 'CRITICAL'
    elif score >= 12:
        level = 'HIGH'
    elif score >= 6:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {
        'ems_score': score,
        'ems_level': level,
        'ems_used': True,
        'ems_name': ems_name,
        'ems_country': ems_country,
        'has_profile': True,
        'financial_health': fin_health,
        'capacity_utilization': capacity_f,
        'backup_sites': backup_n,
        'certifications': list(ems_certs),
        'factors': factors,
        'suggestions': suggestions,
        'breakdown': breakdown,
    }


def _calc_geo_score(country: str) -> int:
    """Calcola punteggio geo per paese EMS."""
    if not country:
        return 0
    country_lower = country.lower().strip()
    for key, score in EMS_COUNTRY_RISK.items():
        if key in country_lower or country_lower in key:
            return score
    return 2  # Default per paesi non mappati


# =============================================================================
# ANALISI BOM - EMS
# =============================================================================

def analyze_bom_ems_risk(
    components_data: list,
    ems_providers_by_name: dict
) -> dict:
    """
    Analizza il rischio EMS a livello BOM.

    Args:
        components_data: Lista componenti dal batch lookup
        ems_providers_by_name: Dict {ems_name: ems_profile} dal DB

    Returns:
        {
            'components_ems': List[Dict],
            'ems_components_count': int,
            'shared_ems_risks': List[Dict],   # EMS usati da molti componenti
            'avg_ems_score': float,
            'critical_ems': List[str],
        }
    """
    components_ems = []
    ems_usage = {}  # ems_name -> [part_numbers]

    for comp in components_data:
        pn = str(comp.get('Part Number', ''))
        ems_name = str(comp.get('EMS_Name', '') or '').strip()
        ems_profile = ems_providers_by_name.get(ems_name.upper()) if ems_name else None

        ems_result = calculate_ems_risk(comp, ems_profile)
        ems_result['part_number'] = pn
        components_ems.append(ems_result)

        if ems_result['ems_used'] and ems_name:
            if ems_name not in ems_usage:
                ems_usage[ems_name] = []
            ems_usage[ems_name].append(pn)

    # Identifica EMS shared (usati da molti componenti → SPOF)
    shared_ems_risks = []
    for ems_name, pns in ems_usage.items():
        if len(pns) >= 2:
            ems_profile = ems_providers_by_name.get(ems_name.upper(), {})
            backup = int(float(ems_profile.get('Backup_Sites_Count', 0) or 0)) if ems_profile else 0
            shared_ems_risks.append({
                'ems_name': ems_name,
                'affected_pns': pns,
                'affected_count': len(pns),
                'backup_sites': backup,
                'is_single_site': backup == 0,
            })
    shared_ems_risks.sort(key=lambda x: x['affected_count'], reverse=True)

    # EMS components count
    ems_components = [c for c in components_ems if c['ems_used']]
    avg_score = (
        sum(c['ems_score'] for c in ems_components) / len(ems_components)
        if ems_components else 0
    )

    critical_ems = [c['part_number'] for c in ems_components if c['ems_score'] >= 20]

    return {
        'components_ems': components_ems,
        'ems_components_count': len(ems_components),
        'shared_ems_risks': shared_ems_risks,
        'avg_ems_score': round(avg_score, 1),
        'critical_ems': critical_ems,
    }
