"""
Distributor Risk Scoring Module - v4.0
========================================
Modulo per il calcolo del rischio distributore nella supply chain commerciale.

Valuta il rischio del canale distributivo (Arrow, Avnet, TTI, Digi-Key, ecc.) in base a:
- Mono-distributor risk (solo 1 distributore per PN)
- Stock coverage del distributore
- Salute finanziaria
- Lead time markup
- Concentrazione geografica

Uso:
    from distributor_risk import calculate_distributor_risk, analyze_bom_distributor_risk
    result = calculate_distributor_risk(component_data, distributor_list)
"""

import pandas as pd
from typing import Dict, Any, List, Optional


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

# Punteggio salute finanziaria distributore
DIST_FINANCIAL_SCORES = {
    'A': 0,
    'B': 2,
    'C': 6,
    'D': 10,
}

# Paesi a rischio per sede distributore
DIST_COUNTRY_RISK = {
    'china': 10,
    'hong_kong': 8,
    'russia': 8,
    'taiwan': 6,
    'korea': 4,
    'japan': 3,
    'singapore': 2,
    'usa': 0,
    'germany': 0,
    'uk': 0,
    'france': 0,
    'netherlands': 0,
    'belgium': 0,
}


# =============================================================================
# FUNZIONI DI UTILITÀ
# =============================================================================

def _safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    val = data.get(key, default)
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    return val


def _calc_country_risk(country: str) -> int:
    if not country:
        return 0
    c = country.lower().strip().replace(' ', '_')
    for key, score in DIST_COUNTRY_RISK.items():
        if key in c or c in key:
            return score
    return 2


# =============================================================================
# CALCOLO RISCHIO DISTRIBUTORE
# =============================================================================

def calculate_distributor_risk(
    component_data: Dict[str, Any],
    distributor_list: List[Dict[str, Any]],
    lead_time_weeks: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calcola il rischio distributore per un componente.

    Args:
        component_data: Dati componente dal DB
        distributor_list: Lista di {Priority, distributor_data} dal DB
        lead_time_weeks: Lead time fornitore (per confronto con stock coverage)

    Returns:
        {
            'distributor_score': int (0-25),
            'has_distributors': bool,
            'primary_distributor': str,
            'distributor_count': int,
            'factors': List[str],
            'suggestions': List[str],
            'breakdown': List[Dict],
        }
    """
    if not distributor_list:
        # Nessun distributore definito: penalità moderata (dato mancante)
        return {
            'distributor_score': 0,
            'has_distributors': False,
            'primary_distributor': '',
            'distributor_count': 0,
            'factors': [],
            'suggestions': ['Definire il canale distributivo per questo componente in Gestione Database → Distributori'],
            'breakdown': [],
        }

    score = 0
    factors = []
    suggestions = []
    breakdown = []

    # Separa primari e secondari
    primary = [d for d in distributor_list if str(_safe_get(d, 'Priority', 'Primary')).strip() == 'Primary']
    secondary = [d for d in distributor_list if str(_safe_get(d, 'Priority', 'Primary')).strip() == 'Secondary']

    primary_dist = primary[0] if primary else distributor_list[0]
    primary_data = primary_dist.get('distributor_data', {}) or {}
    primary_name = str(_safe_get(primary_data, 'Name', 'N/A') or 'N/A')

    # Lead time del componente
    try:
        lt = int(float(lead_time_weeks or _safe_get(component_data, 'Supplier Lead Time (weeks)', 12) or 12))
    except (ValueError, TypeError):
        lt = 12

    # =========================================================================
    # 1. MONO-DISTRIBUTORE (max 10 punti)
    # =========================================================================
    n_dist = len(distributor_list)
    if n_dist == 1 and not secondary:
        mono_score = 10
        factors.append(f"🚚 CRITICO: Mono-distributore ({primary_name}) - nessun canale alternativo")
        suggestions.append("Qualificare un secondo distributore come backup")
    elif n_dist <= 2 and not secondary:
        mono_score = 5
        factors.append(f"🚚 ALTO: Solo {n_dist} distributori, nessuno secondario qualificato")
        suggestions.append("Aggiungere distributore secondario qualificato")
    else:
        mono_score = 0
        if len(secondary) >= 1:
            factors.append(f"✅ OK: {n_dist} distributori ({len(secondary)} secondari qualificati)")
    score += mono_score
    breakdown.append({'factor': f'Mono-distributor (n={n_dist})', 'score': mono_score})

    # =========================================================================
    # 2. STOCK COVERAGE (max 8 punti)
    # =========================================================================
    stock_weeks = _safe_get(primary_data, 'Stock_Level_Weeks_Coverage', 0)
    try:
        stock_f = float(stock_weeks) if stock_weeks is not None else 0
    except (ValueError, TypeError):
        stock_f = 0

    if stock_f <= 0:
        stock_score = 8
        factors.append(f"📦 CRITICO: Nessun dato stock distributore {primary_name}")
        suggestions.append("Richiedere dati stock al distributore primario")
    elif stock_f < lt * 0.5:
        stock_score = 8
        factors.append(f"📦 CRITICO: Stock distributore ({stock_f:.1f} sett.) < 50% del lead time ({lt} sett.)")
        suggestions.append(f"Negoziare VMI o buffer dedicato con {primary_name}")
    elif stock_f < lt:
        stock_score = 4
        factors.append(f"📦 ALTO: Stock distributore ({stock_f:.1f} sett.) inferiore al lead time ({lt} sett.)")
    elif stock_f >= lt * 2:
        stock_score = -2  # Bonus
        factors.append(f"✅ MITIGATO: Stock distributore ampio ({stock_f:.1f} sett. = {stock_f/lt:.1f}x lead time)")
    else:
        stock_score = 0
    score += stock_score
    breakdown.append({'factor': f'Stock Coverage ({stock_f:.1f}w)', 'score': stock_score})

    # =========================================================================
    # 3. SALUTE FINANZIARIA DISTRIBUTORE (max 10 punti)
    # =========================================================================
    fin_health = str(_safe_get(primary_data, 'Financial_Health', 'A') or 'A').strip().upper()
    fin_score = DIST_FINANCIAL_SCORES.get(fin_health, 0)
    score += fin_score
    breakdown.append({'factor': f'Financial Health ({fin_health})', 'score': fin_score})
    if fin_score >= 6:
        factors.append(f"💰 ALTO: Salute finanziaria distributore rating {fin_health}")
        suggestions.append(f"Monitorare stabilità finanziaria di {primary_name}")
    elif fin_score >= 2:
        factors.append(f"💰 MEDIO: Salute finanziaria distributore {fin_health}")

    # =========================================================================
    # 4. LEAD TIME MARKUP (max 5 punti)
    # =========================================================================
    markup_weeks = _safe_get(primary_data, 'Lead_Time_Markup_Weeks', 0)
    try:
        markup_f = int(float(markup_weeks)) if markup_weeks is not None else 0
    except (ValueError, TypeError):
        markup_f = 0

    if markup_f >= 8:
        markup_score = 5
        factors.append(f"⏱️ ALTO: Lead time markup distributore +{markup_f} settimane")
        suggestions.append("Negoziare accordo VMI per ridurre lead time markup")
    elif markup_f >= 4:
        markup_score = 3
        factors.append(f"⏱️ MEDIO: Lead time markup distributore +{markup_f} settimane")
    elif markup_f >= 2:
        markup_score = 1
    else:
        markup_score = 0
    score += markup_score
    breakdown.append({'factor': f'Lead Time Markup (+{markup_f}w)', 'score': markup_score})

    # =========================================================================
    # 5. CONCENTRAZIONE GEOGRAFICA DISTRIBUTORE (max 5 punti)
    # =========================================================================
    dist_country = str(_safe_get(primary_data, 'Country', '') or '').strip()
    geo_score = _calc_country_risk(dist_country)
    geo_score = min(5, geo_score)  # Cap a 5 per distributore
    score += geo_score
    breakdown.append({'factor': f'Geo Risk ({dist_country.title() if dist_country else "N/A"})', 'score': geo_score})
    if geo_score >= 5:
        factors.append(f"🌏 ALTO: Distributore primario in {dist_country.title()} - rischio geopolitico")

    # Cap a 25
    score = max(0, min(25, score))

    # Classificazione
    if score >= 18:
        level = 'CRITICO'
    elif score >= 10:
        level = 'ALTO'
    elif score >= 5:
        level = 'MEDIO'
    else:
        level = 'BASSO'

    return {
        'distributor_score': score,
        'distributor_level': level,
        'has_distributors': True,
        'primary_distributor': primary_name,
        'distributor_count': n_dist,
        'secondary_count': len(secondary),
        'stock_coverage_weeks': stock_f,
        'lead_time_markup_weeks': markup_f,
        'factors': factors,
        'suggestions': suggestions,
        'breakdown': breakdown,
    }


# =============================================================================
# ANALISI BOM - DISTRIBUTORI
# =============================================================================

def analyze_bom_distributor_risk(
    components_data: List[Dict[str, Any]],
    part_distributors: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Analisi rischio distributori a livello BOM.

    Args:
        components_data: Lista componenti dal lookup
        part_distributors: Dict {pn: [distributor_records]} dal DB

    Returns:
        {
            'components_distributor': List[Dict],
            'distributor_concentration': Dict[str, Dict],  # distributore -> {pns, avg_score}
            'mono_distributor_pns': List[str],
            'no_distributor_pns': List[str],
            'avg_distributor_score': float,
            'top_shared_distributors': List[Dict],
        }
    """
    components_distributor = []
    distributor_usage = {}   # dist_name -> [pns]
    mono_pns = []
    no_dist_pns = []
    total_score = 0
    count_with_dist = 0

    for comp in components_data:
        pn = str(comp.get('Part Number', ''))
        pn_upper = pn.upper()
        dist_list = part_distributors.get(pn_upper, [])

        try:
            lt = int(float(comp.get('Supplier Lead Time (weeks)', 12) or 12))
        except (ValueError, TypeError):
            lt = 12

        dist_result = calculate_distributor_risk(comp, dist_list, lt)
        dist_result['part_number'] = pn
        components_distributor.append(dist_result)

        if not dist_result['has_distributors']:
            no_dist_pns.append(pn)
        else:
            count_with_dist += 1
            total_score += dist_result['distributor_score']

            if dist_result['distributor_count'] == 1:
                mono_pns.append(pn)

            # Traccia utilizzo distributore
            primary = dist_result['primary_distributor']
            if primary and primary != 'N/A':
                if primary not in distributor_usage:
                    distributor_usage[primary] = []
                distributor_usage[primary].append(pn)

    # Top distributori condivisi (SPOF potenziale)
    top_shared = []
    for dist_name, pns in sorted(distributor_usage.items(), key=lambda x: len(x[1]), reverse=True):
        if len(pns) >= 2:
            top_shared.append({
                'distributor': dist_name,
                'affected_pns': pns,
                'affected_count': len(pns),
                'is_spof': len(pns) >= 3,
            })

    avg_score = total_score / count_with_dist if count_with_dist > 0 else 0

    return {
        'components_distributor': components_distributor,
        'distributor_concentration': distributor_usage,
        'mono_distributor_pns': mono_pns,
        'no_distributor_pns': no_dist_pns,
        'avg_distributor_score': round(avg_score, 1),
        'top_shared_distributors': top_shared,
    }


# =============================================================================
# SIMULATORE STOCK-OUT DISTRIBUTORE
# =============================================================================

def simulate_distributor_stockout(
    components_data: List[Dict[str, Any]],
    part_distributors: Dict[str, List[Dict[str, Any]]],
    target_distributor: str,
    stockout_weeks: int,
    run_rate: int
) -> Dict[str, Any]:
    """
    Simula l'impatto di uno stock-out su un distributore specifico.

    Args:
        components_data: Lista componenti
        part_distributors: Dict {pn: [distributor_records]}
        target_distributor: Nome distributore da simulare
        stockout_weeks: Settimane di stock-out
        run_rate: PCB/settimana

    Returns:
        {
            'affected_pns': List[str],
            'critical_pns': List[str],   # buffer esaurito entro stockout
            'summary': Dict,
        }
    """
    affected = []
    critical = []

    for comp in components_data:
        pn = str(comp.get('Part Number', ''))
        pn_upper = pn.upper()
        dist_list = part_distributors.get(pn_upper, [])

        # Controlla se questo PN usa il distributore target
        uses_target = False
        has_secondary = False
        for d in dist_list:
            d_data = d.get('distributor_data', {}) or {}
            d_name = str(_safe_get(d_data, 'Name', '') or '').strip()
            if d_name.upper() == target_distributor.upper():
                uses_target = True
            if str(_safe_get(d, 'Priority', 'Primary')).strip() == 'Secondary':
                has_secondary = True

        if not uses_target:
            continue

        # Calcola buffer disponibile
        buffer = float(comp.get('If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units', 0) or 0)
        qty = float(comp.get('How Many Device of this specific PN are in the BOM?', 1) or 1)
        if qty <= 0:
            qty = 1
        weekly_consumption = run_rate * qty
        buffer_weeks = buffer / weekly_consumption if weekly_consumption > 0 else 0

        is_critical = buffer_weeks < stockout_weeks and not has_secondary
        weeks_lost = max(0, stockout_weeks - buffer_weeks) if not has_secondary else 0

        comp_impact = {
            'part_number': pn,
            'supplier': str(comp.get('Supplier Name', 'N/A')),
            'has_secondary_distributor': has_secondary,
            'buffer_weeks': round(buffer_weeks, 1),
            'weeks_lost': round(weeks_lost, 1),
            'is_critical': is_critical,
        }
        affected.append(comp_impact)
        if is_critical:
            critical.append(pn)

    return {
        'target_distributor': target_distributor,
        'stockout_weeks': stockout_weeks,
        'affected_components': affected,
        'affected_count': len(affected),
        'critical_pns': critical,
        'critical_count': len(critical),
        'summary': {
            'total_affected': len(affected),
            'total_critical': len(critical),
            'avg_weeks_lost': (
                sum(c['weeks_lost'] for c in affected) / len(affected)
                if affected else 0
            ),
        },
    }
