"""
Geographic Risk Engine - Frontend/Backend Analysis
===================================================
Modulo per la valutazione del rischio geopolitico stratificato
distinguendo la fase di fabbricazione wafer (frontend) dalla fase
di assemblaggio e test (backend).

Uso:
    from geo_risk import calculate_geo_risk, get_technology_node_risk
"""

import pandas as pd
from typing import Dict, Any, List, Optional


# =============================================================================
# CONFIGURAZIONE RISCHIO GEOGRAFICO
# =============================================================================

# Rischio Frontend (fabbricazione wafer) - peso 60% dello score geo
FRONTEND_RISK_SCORES = {
    'taiwan': {'score': 25, 'level': 'CRITICAL', 'reason': '60% concentration of global wafer production'},
    'china': {'score': 20, 'level': 'HIGH', 'reason': 'Geopolitical risk + export controls'},
    'korea': {'score': 15, 'level': 'MEDIUM-HIGH', 'reason': 'Samsung/SK Hynix concentration'},
    'japan': {'score': 12, 'level': 'MEDIUM', 'reason': 'Seismic risk + aging fabs'},
    'singapore': {'score': 8, 'level': 'MEDIUM-LOW', 'reason': 'Stable but small hub'},
    'malaysia': {'score': 10, 'level': 'MEDIUM', 'reason': 'Growing hub'},
    'usa': {'score': 5, 'level': 'LOW', 'reason': 'Diversification in progress (CHIPS Act)'},
    'germany': {'score': 3, 'level': 'LOW', 'reason': 'Stable European hub'},
    'france': {'score': 3, 'level': 'LOW', 'reason': 'Stable European hub (ST Crolles)'},
    'italy': {'score': 3, 'level': 'LOW', 'reason': 'European hub (ST Catania/Agrate)'},
    'ireland': {'score': 3, 'level': 'LOW', 'reason': 'Intel EU hub'},
    'israel': {'score': 8, 'level': 'MEDIUM-LOW', 'reason': 'Intel/Tower hub, regional risk'},
}

# Rischio Backend (assemblaggio/test OSAT) - peso 40% dello score geo
BACKEND_RISK_SCORES = {
    'malaysia': {'score': 15, 'level': 'HIGH', 'reason': 'Main OSAT concentration'},
    'philippines': {'score': 15, 'level': 'HIGH', 'reason': 'OSAT concentration'},
    'china': {'score': 12, 'level': 'MEDIUM-HIGH', 'reason': 'JCET/tariff risk'},
    'taiwan': {'score': 10, 'level': 'MEDIUM', 'reason': 'ASE Group, geopolitical risk'},
    'korea': {'score': 8, 'level': 'MEDIUM-LOW', 'reason': 'Samsung backend'},
    'thailand': {'score': 10, 'level': 'MEDIUM', 'reason': 'Growing hub'},
    'vietnam': {'score': 10, 'level': 'MEDIUM', 'reason': 'Emerging hub'},
    'singapore': {'score': 5, 'level': 'LOW', 'reason': 'Stable hub'},
    'usa': {'score': 3, 'level': 'LOW', 'reason': 'Limited but secure backend'},
    'germany': {'score': 2, 'level': 'LOW', 'reason': 'European backend'},
    'france': {'score': 2, 'level': 'LOW', 'reason': 'European backend'},
    'italy': {'score': 2, 'level': 'LOW', 'reason': 'European backend'},
}

# Technology Node risk
TECH_NODE_THRESHOLDS = [
    {'max_nm': 7, 'score': 25, 'level': 'CRITICAL',
     'reason': 'Only TSMC/Samsung, no EU/USA alternative'},
    {'max_nm': 14, 'score': 20, 'level': 'HIGH',
     'reason': 'Few foundries (TSMC, Samsung, Intel)'},
    {'max_nm': 28, 'score': 15, 'level': 'MEDIUM-HIGH',
     'reason': 'Limited foundries, GlobalFoundries/SMIC partial'},
    {'max_nm': 65, 'score': 8, 'level': 'MEDIUM',
     'reason': 'More foundries available including EU'},
    {'max_nm': 130, 'score': 5, 'level': 'LOW',
     'reason': 'Wide global availability'},
    {'max_nm': float('inf'), 'score': 3, 'level': 'LOW',
     'reason': 'Legacy nodes, long-term obsolescence risk'},
]

FRONTEND_WEIGHT = 0.6
BACKEND_WEIGHT = 0.4


# =============================================================================
# FUNZIONI PRINCIPALI
# =============================================================================

def _normalize_country(country: str) -> str:
    """Normalizza il nome del paese per matching."""
    if not country:
        return ''
    country = str(country).strip().lower()
    # Alias comuni
    aliases = {
        'united states': 'usa', 'us': 'usa', 'u.s.a.': 'usa', 'united states of america': 'usa',
        'south korea': 'korea', 'republic of korea': 'korea',
        'people\'s republic of china': 'china', 'prc': 'china',
        'uk': 'united kingdom', 'great britain': 'united kingdom',
        'deutschland': 'germany', 'de': 'germany',
    }
    return aliases.get(country, country)


def _get_safe(row: Dict[str, Any], key: str, default: Any = '') -> Any:
    """Ottiene un valore in modo sicuro."""
    val = row.get(key, default)
    if pd.isna(val) if isinstance(val, float) else not val:
        return default
    return val


def calculate_geo_risk(component: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcola il rischio geopolitico separando frontend (wafer fab) e backend (assembly/test).

    Args:
        component: Dizionario con i dati del componente. Usa:
            - Frontend_Country
            - Backend_Country
            - Country of Manufacturing Plant 1-4 (fallback)

    Returns:
        Dizionario con frontend_risk, backend_risk, composite_score, factors, suggestions
    """
    frontend_country = _normalize_country(_get_safe(component, 'Frontend_Country'))
    backend_country = _normalize_country(_get_safe(component, 'Backend_Country'))

    # Fallback: se frontend/backend non specificati, usa Plant 1 come frontend
    if not frontend_country:
        frontend_country = _normalize_country(
            _get_safe(component, 'Country of Manufacturing Plant 1')
        )
    if not backend_country:
        # Usa Plant 2 come backend se disponibile, altrimenti stesso del frontend
        backend_country = _normalize_country(
            _get_safe(component, 'Country of Manufacturing Plant 2', '')
        )
        if not backend_country:
            backend_country = frontend_country

    # Calculate frontend risk
    frontend_info = FRONTEND_RISK_SCORES.get(frontend_country, {
        'score': 10, 'level': 'UNKNOWN', 'reason': f'Unclassified country: {frontend_country}'
    })

    # Calculate backend risk
    backend_info = BACKEND_RISK_SCORES.get(backend_country, {
        'score': 8, 'level': 'UNKNOWN', 'reason': f'Unclassified country: {backend_country}'
    })

    # Score composito
    composite_score = (
        frontend_info['score'] * FRONTEND_WEIGHT +
        backend_info['score'] * BACKEND_WEIGHT
    )

    # Costruisci fattori
    factors = []
    suggestions = []

    if frontend_info['score'] >= 20:
        factors.append(
            f"FAB FRONTEND {frontend_info['level']}: {frontend_country.title()} - {frontend_info['reason']}"
        )
        suggestions.append("Evaluate suppliers with frontend in EU/USA (CHIPS Act, European Chips Act)")
    elif frontend_info['score'] >= 10:
        factors.append(
            f"FAB FRONTEND {frontend_info['level']}: {frontend_country.title()} - {frontend_info['reason']}"
        )

    if backend_info['score'] >= 12:
        factors.append(
            f"ASSEMBLY BACKEND {backend_info['level']}: {backend_country.title()} - {backend_info['reason']}"
        )
        suggestions.append("Consider OSAT with sites in multiple regions")
    elif backend_info['score'] >= 8:
        factors.append(
            f"ASSEMBLY BACKEND {backend_info['level']}: {backend_country.title()} - {backend_info['reason']}"
        )

    # Determine composite level
    if composite_score >= 20:
        level = 'CRITICAL'
    elif composite_score >= 12:
        level = 'HIGH'
    elif composite_score >= 6:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {
        'frontend_country': frontend_country,
        'frontend_score': frontend_info['score'],
        'frontend_level': frontend_info['level'],
        'frontend_reason': frontend_info['reason'],
        'backend_country': backend_country,
        'backend_score': backend_info['score'],
        'backend_level': backend_info['level'],
        'backend_reason': backend_info['reason'],
        'composite_score': round(composite_score, 1),
        'composite_level': level,
        'factors': factors,
        'suggestions': suggestions,
    }


def get_technology_node_risk(tech_node: Any) -> Dict[str, Any]:
    """
    Valuta il rischio basato sul nodo tecnologico del chip.

    Args:
        tech_node: Nodo tecnologico (es. "28nm", "180nm", 7, "28")

    Returns:
        Dizionario con score, level, reason
    """
    if not tech_node or (isinstance(tech_node, float) and pd.isna(tech_node)):
        return {'score': 0, 'level': 'N/A', 'reason': 'Technology node not specified', 'nm': None}

    # Parsing: accetta "28nm", "28", 28, "7nm", etc.
    tech_str = str(tech_node).lower().replace('nm', '').replace(' ', '')
    try:
        nm_value = float(tech_str)
    except ValueError:
        return {'score': 0, 'level': 'N/A', 'reason': f'Unrecognized format: {tech_node}', 'nm': None}

    for threshold in TECH_NODE_THRESHOLDS:
        if nm_value <= threshold['max_nm']:
            return {
                'score': threshold['score'],
                'level': threshold['level'],
                'reason': threshold['reason'],
                'nm': nm_value,
            }

    return {'score': 3, 'level': 'LOW', 'reason': 'Legacy node', 'nm': nm_value}


def generate_risk_map_data(components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Genera dati per la visualizzazione su mappa Folium.

    Args:
        components: Lista di componenti con dati geo

    Returns:
        Lista di marker con coordinate, tipo (frontend/backend), rischio
    """
    # Coordinate approssimative dei principali hub produttivi
    COUNTRY_COORDS = {
        'taiwan': (23.5, 121.0),
        'china': (31.2, 121.5),
        'korea': (37.5, 127.0),
        'japan': (35.7, 139.7),
        'malaysia': (3.1, 101.7),
        'philippines': (14.6, 121.0),
        'singapore': (1.3, 103.8),
        'thailand': (13.8, 100.5),
        'vietnam': (21.0, 105.8),
        'usa': (37.4, -122.1),
        'germany': (48.1, 11.6),
        'france': (45.2, 5.7),
        'italy': (37.5, 15.1),
        'ireland': (53.3, -6.3),
        'israel': (32.1, 34.8),
        'united kingdom': (51.5, -0.1),
        'mexico': (23.6, -102.6),
    }

    import random

    def get_coords(country: str | None) -> tuple | None:
        """Helper per lookup case-insensitive delle coordinate."""
        if not country:
            return None
        return COUNTRY_COORDS.get(country.lower())

    # Aggiunge un piccolo jitter per evitare sovrapposizione dei marker
    def jitter_coords(lat: float, lon: float, index: int) -> tuple:
        """Sposta leggermente le coordinate in base all'indice."""
        # Jitter di circa ±0.5 gradi (circa 50km)
        lat_offset = (index % 5 - 2) * 0.2
        lon_offset = ((index // 5) % 5 - 2) * 0.2
        return (lat + lat_offset, lon + lon_offset)

    markers = []
    frontend_count = {}  # Contatore per jitter frontend per paese
    backend_count = {}   # Contatore per jitter backend per paese

    for comp in components:
        pn = _get_safe(comp, 'Part Number', 'N/A')
        supplier = _get_safe(comp, 'Supplier Name', 'N/A')

        geo = calculate_geo_risk(comp)

        # Frontend marker
        frontend_country = geo['frontend_country'].lower() if geo['frontend_country'] else ''
        frontend_coords = get_coords(geo['frontend_country'])
        if frontend_coords:
            idx = frontend_count.get(frontend_country, 0)
            frontend_count[frontend_country] = idx + 1
            lat_jit, lon_jit = jitter_coords(frontend_coords[0], frontend_coords[1], idx)
            markers.append({
                'lat': lat_jit,
                'lon': lon_jit,
                'type': 'frontend',
                'part_number': pn,
                'supplier': supplier,
                'country': geo['frontend_country'].title(),
                'risk_score': geo['frontend_score'],
                'risk_level': geo['frontend_level'],
                'label': f"FAB: {pn} ({supplier})",
            })

        # Backend marker
        backend_country = geo['backend_country'].lower() if geo['backend_country'] else ''
        backend_coords = get_coords(geo['backend_country'])
        if backend_coords:
            idx = backend_count.get(backend_country, 0)
            backend_count[backend_country] = idx + 1
            lat_jit, lon_jit = jitter_coords(backend_coords[0], backend_coords[1], idx + 100)  # +100 per separare da frontend
            markers.append({
                'lat': lat_jit,
                'lon': lon_jit,
                'type': 'backend',
                'part_number': pn,
                'supplier': supplier,
                'country': geo['backend_country'].title(),
                'risk_score': geo['backend_score'],
                'risk_level': geo['backend_level'],
                'label': f"OSAT: {pn} ({supplier})",
            })

    return markers
