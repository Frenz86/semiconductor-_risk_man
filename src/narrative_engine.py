"""
narrative_engine.py — Generazione automatica di testi descrittivi del rischio (v4.2)
Template-based: nessun LLM esterno richiesto.
"""


# Descrizioni per ogni fattore di rischio
_FACTOR_LABELS = {
    'geo_risk': 'geographic concentration risk (frontend fab)',
    'tech_node_risk': 'advanced technology node dependency',
    'single_source': 'single source / sole supplier',
    'lead_time': 'critical lead time',
    'buffer_stock': 'insufficient buffer stock coverage',
    'functional_dependency': 'functional dependency on other components',
    'proprietary': 'proprietary / non-commodity component',
    'certification': 'long qualification/certification time',
    'eol_status': 'end-of-life or NRND status',
    'alternative_sources': 'no alternative sources available',
    'financial_health': 'poor supplier financial health',
    'allocation': 'component in allocation/shortage status',
    'price_increase': 'significant recent price increase',
    'package_type': 'advanced package type (hard to substitute)',
    'tier2_risk': 'Tier-2 raw material concentration risk',
    'ems_risk': 'EMS provider risk',
    'distributor_risk': 'distributor risk',
    'hidden_spof': 'hidden single point of failure (alternative sources converge on same country)',
    'ip_risk': 'IP/SW dependency risk (abandoned or proprietary stack)',
    'shortage_risk': 'active market shortage for this component interface',
}

_RECOMMENDATIONS = {
    'geo_risk': 'Qualify an alternative supplier with manufacturing outside {country}.',
    'single_source': 'Identify and qualify a second source to eliminate SPOF.',
    'lead_time': 'Increase buffer stock to cover at least 2x lead time ({lead_time}w).',
    'buffer_stock': 'Current buffer ({buffer_weeks:.0f}w) is below lead time ({lead_time}w). Increase stock.',
    'eol_status': 'Initiate last-time-buy or redesign with active replacement.',
    'alternative_sources': 'Register at least one alternative source in the database.',
    'hidden_spof': 'Alternative sources converge on {country}. Diversify by country.',
    'ip_risk': 'Migrate to actively maintained IP stack or open-source alternative.',
    'shortage_risk': 'Increase safety stock; monitor market availability weekly.',
    'allocation': 'Expedite orders; contact distributor for allocation priority.',
    'default': 'Review supplier contract and activate contingency plan.',
}


def _top_factors(r: dict, n: int = 3) -> list[tuple[str, float]]:
    """
    Estrae i top-n fattori di rischio per score dal risultato componente.
    Restituisce lista di (factor_key, score_contribution).
    """
    factors = {}

    geo = r.get('geo_risk', {})
    if isinstance(geo, dict):
        factors['geo_risk'] = geo.get('composite_score', 0)

    if r.get('is_spof'):
        factors['single_source'] = 20

    lt = r.get('lead_time', 0)
    try:
        lt_val = float(lt)
    except (TypeError, ValueError):
        lt_val = 0
    if lt_val >= 10:
        factors['lead_time'] = 15 if lt_val >= 16 else 10

    buf_weeks = r.get('buffer_coverage_weeks', 999)
    if buf_weeks < lt_val:
        factors['buffer_stock'] = 15

    eol = str(r.get('eol_status', '')).upper()
    if eol in ('EOL', 'OBSOLETE', 'LAST_BUY', 'NRND'):
        factors['eol_status'] = 15 if eol in ('EOL', 'OBSOLETE') else 8

    alt_count = r.get('alternative_sources_count', 1)
    if alt_count == 0:
        factors['alternative_sources'] = 10

    hidden = r.get('hidden_spof', {})
    if isinstance(hidden, dict) and hidden.get('hidden_spof_score', 0) >= 4:
        factors['hidden_spof'] = hidden.get('hidden_spof_score', 0)

    ip = r.get('ip_risk', {})
    if isinstance(ip, dict) and ip.get('ip_score', 0) >= 5:
        factors['ip_risk'] = ip.get('ip_score', 0)

    alloc = str(r.get('allocation_status', '')).upper()
    if alloc == 'ALLOCATED':
        factors['allocation'] = 10
    elif alloc == 'CONSTRAINED':
        factors['allocation'] = 5

    shortage = r.get('shortage_penalty', 0)
    if shortage >= 5:
        factors['shortage_risk'] = shortage

    ems = r.get('ems_detail', {})
    if isinstance(ems, dict) and ems.get('ems_score', 0) >= 8:
        factors['ems_risk'] = ems.get('ems_score', 0)

    dist = r.get('distributor_detail', {})
    if isinstance(dist, dict) and dist.get('distributor_score', 0) >= 6:
        factors['distributor_risk'] = dist.get('distributor_score', 0)

    sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
    return sorted_factors[:n]


def generate_risk_narrative(r: dict) -> str:
    """
    Genera un paragrafo descrittivo del rischio per un singolo componente.

    Args:
        r: Dizionario risultato di calculate_component_risk()

    Returns:
        Stringa di testo narrativo (1-4 frasi)
    """
    pn = r.get('part_number', 'N/A')
    supplier = r.get('supplier', 'N/A')
    score = r.get('score', 0)
    level = r.get('risk_level', r.get('color', ''))
    if level == 'RED':
        level_label = 'HIGH'
    elif level == 'YELLOW':
        level_label = 'MEDIUM'
    else:
        level_label = 'LOW'

    top = _top_factors(r)
    if not top:
        return f"{pn} ({supplier}) — Risk score: {score:.0f}/100. No critical risk factors detected."

    # Prima frase: introduzione
    factor_names = [_FACTOR_LABELS.get(f, f) for f, _ in top]
    if len(factor_names) == 1:
        drivers = factor_names[0]
    elif len(factor_names) == 2:
        drivers = f"{factor_names[0]} and {factor_names[1]}"
    else:
        drivers = f"{factor_names[0]}, {factor_names[1]}, and {factor_names[2]}"

    narrative = (
        f"**{pn}** ({supplier}) shows **{level_label} risk** (score {score:.0f}/100). "
        f"The main risk drivers are: {drivers}."
    )

    # Seconda frase: dettaglio primo fattore
    top_factor, _ = top[0]
    geo = r.get('geo_risk', {})
    frontend_country = geo.get('frontend_country', '') if isinstance(geo, dict) else ''
    lt = r.get('lead_time', 0)
    buf = r.get('buffer_coverage_weeks', 0)

    if top_factor == 'geo_risk' and frontend_country:
        narrative += f" Frontend wafer fabrication is concentrated in **{frontend_country}**."
    elif top_factor == 'single_source':
        narrative += " This component has **only one known supplier**, creating a critical dependency."
    elif top_factor == 'lead_time':
        narrative += f" Lead time of **{lt} weeks** significantly limits reaction time to disruptions."
    elif top_factor == 'buffer_stock':
        narrative += f" Buffer stock covers only **{buf:.0f} weeks** versus a lead time of **{lt} weeks**."
    elif top_factor == 'hidden_spof':
        hidden = r.get('hidden_spof', {})
        country = hidden.get('overlap_country', '') if isinstance(hidden, dict) else ''
        narrative += f" All alternative sources converge on **{country}** — effectively a hidden SPOF."
    elif top_factor == 'eol_status':
        narrative += f" Status is **{r.get('eol_status', 'EOL')}** — last-time-buy or redesign required."

    # Terza frase: raccomandazione principale
    rec_template = _RECOMMENDATIONS.get(top_factor, _RECOMMENDATIONS['default'])
    try:
        rec = rec_template.format(
            country=frontend_country or 'the primary country',
            lead_time=lt,
            buffer_weeks=buf,
        )
    except (KeyError, ValueError):
        rec = _RECOMMENDATIONS['default']
    narrative += f" **Recommended action**: {rec}"

    return narrative


def generate_bom_narrative_summary(components_risk: list, bom_risk: dict) -> str:
    """
    Genera un sommario testuale della BOM intera.

    Args:
        components_risk: Lista risultati componenti
        bom_risk: Risultato calculate_bom_risk_v3()

    Returns:
        Stringa testo sommario (3-5 frasi)
    """
    if not components_risk:
        return "No components analyzed."

    total = len(components_risk)
    high = sum(1 for r in components_risk if r.get('color') == 'RED')
    spofs = len(bom_risk.get('spofs', []))
    avg = sum(r.get('score', 0) for r in components_risk) / total
    bom_level = bom_risk.get('risk_level', 'N/A')

    summary = (
        f"The BOM contains **{total} components** with an average risk score of **{avg:.1f}/100** "
        f"(BOM level: **{bom_level}**). "
        f"**{high} components** are classified HIGH risk and require immediate attention. "
    )

    if spofs:
        summary += f"**{spofs} critical SPOF** components were identified — supply interruption of any one could halt production. "

    # Identifica paese più rischioso
    country_scores = {}
    for r in components_risk:
        geo = r.get('geo_risk', {})
        if isinstance(geo, dict):
            fc = geo.get('frontend_country', '')
            if fc:
                country_scores[fc] = country_scores.get(fc, 0) + r.get('score', 0)
    if country_scores:
        top_country = max(country_scores, key=country_scores.get)
        summary += f"The highest geographic concentration is in **{top_country}**."

    return summary
