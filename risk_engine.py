"""
Risk Engine - Supply Chain Risk Assessment v3.0
===============================================
Motore di calcolo del rischio per componenti elettronici.

v3.0: Integra geo_risk (frontend/backend), switching_cost e dependency_graph.

Modulo indipendente da Streamlit per la logica di business del calcolo del rischio.
Può essere importato e utilizzato in altri contesti (API, CLI, test, etc.).

Uso:
    from risk_engine import calculate_component_risk, calculate_bom_risk_v3

    risk = calculate_component_risk(component_data, run_rate=5000)
"""

import pandas as pd
from typing import Dict, List, Any, Optional

from geo_risk import calculate_geo_risk, get_technology_node_risk
from switching_cost import calculate_switching_cost
from dependency_graph import (
    build_dependency_graph, calculate_chain_risk,
    find_single_points_of_failure, render_dependency_tree
)


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

# Paesi considerati ad alto rischio (legacy, mantenuto per retrocompatibilità)
HIGH_RISK_COUNTRIES = [
    'taiwan', 'china', 'korea', 'japan',
    'malaysia', 'singapore', 'philippines'
]

# Soglie di rischio
RISK_THRESHOLDS = {
    'high': 55,    # Score >= 55 -> RED
    'medium': 30   # Score >= 30 -> YELLOW
}

# Soglie lead time (settimane)
LEAD_TIME_THRESHOLDS = {
    'critical': 16,  # > 16 -> critico
    'high': 10,      # > 10 -> alto
    'medium': 6      # > 6 -> medio
}


# =============================================================================
# FUNZIONI DI UTILITÀ
# =============================================================================

def _extract_countries(row: Dict[str, Any]) -> List[str]:
    """Estrae la lista dei paesi degli stabilimenti produttivi."""
    countries = []
    for col in ['Country of Manufacturing Plant 1', 'Country of Manufacturing Plant 2',
                'Country of Manufacturing Plant 3', 'Country of Manufacturing Plant 4']:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            countries.append(str(row[col]).strip())
    return countries


def _get_safe_value(row: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Ottiene un valore dal dizionario in modo sicuro, gestendo valori NaN."""
    if key not in row:
        return default
    value = row[key]
    if pd.isna(value):
        return default
    return value


# =============================================================================
# MOTORE DI CALCOLO DEL RISCHIO v3.0
# =============================================================================

def calculate_component_risk(row: Dict[str, Any], run_rate: int) -> Dict[str, Any]:
    """
    Calcola il rischio per un singolo componente.

    v3.0: Include geo risk frontend/backend, technology node risk,
    e switching cost nel risultato.

    Args:
        row: Dizionario con i dati del componente
        run_rate: Tasso di produzione (PCB/settimana)

    Returns:
        Dizionario con:
            - score: Punteggio di rischio (0-100)
            - color: 'RED', 'YELLOW', o 'GREEN'
            - risk_level: 'ALTO', 'MEDIO', o 'BASSO'
            - factors: Lista di fattori di rischio identificati
            - suggestions: Lista di suggerimenti per mitigazione
            - man_hours: Stima ore-uomo per mitigazione
            - geo_risk: Dettaglio rischio geografico frontend/backend
            - tech_node_risk: Dettaglio rischio technology node
            - switching_cost: Dettaglio costo di switching
    """
    score = 0
    factors = []
    suggestions = []
    man_hours = 0

    # =====================================================================
    # 1. RISCHIO CONCENTRAZIONE GEOGRAFICA v3 - FRONTEND/BACKEND (25%)
    # =====================================================================
    geo = calculate_geo_risk(row)
    tech_node = get_technology_node_risk(_get_safe_value(row, 'Technology_Node', ''))

    # Usa il composite score geo normalizzato a 25 punti max
    # geo composite_score va da 0 a ~25, lo usiamo direttamente
    geo_score_normalized = min(25, geo['composite_score'])

    if geo_score_normalized >= 20:
        score += 25
        factors.append(f"🌏 CRITICO: Frontend {geo['frontend_country'].title()} ({geo['frontend_level']}) + Backend {geo['backend_country'].title()} ({geo['backend_level']})")
        suggestions.extend(geo['suggestions'])
        man_hours += 40
    elif geo_score_normalized >= 12:
        score += 18
        factors.append(f"🌏 ALTO: Frontend {geo['frontend_country'].title()} ({geo['frontend_level']}) + Backend {geo['backend_country'].title()} ({geo['backend_level']})")
        if geo['suggestions']:
            suggestions.extend(geo['suggestions'])
        man_hours += 30
    elif geo_score_normalized >= 6:
        score += 12
        factors.append(f"🌏 MEDIO: Frontend {geo['frontend_country'].title()} + Backend {geo['backend_country'].title()}")
    else:
        # Basso rischio geo, ma registra comunque info
        if geo['frontend_country']:
            factors.append(f"🌏 BASSO: Frontend {geo['frontend_country'].title()} + Backend {geo['backend_country'].title()}")

    # Bonus/malus per technology node (aggiunge fino a +5 punti)
    if tech_node['score'] >= 20:
        score += 5
        factors.append(f"🔬 ALTO: Nodo tecnologico {tech_node.get('nm', '?')}nm - {tech_node['reason']}")
        suggestions.append("Valutare chip con nodi più maturi o fonderie alternative")
    elif tech_node['score'] >= 10:
        score += 3
        factors.append(f"🔬 MEDIO: Nodo tecnologico {tech_node.get('nm', '?')}nm - {tech_node['reason']}")

    # =====================================================================
    # 2. RISCHIO SINGLE SOURCE (20%)
    # =====================================================================
    countries = _extract_countries(row)
    num_plants = len(countries)

    if num_plants == 1:
        score += 20
        factors.append("🏭 CRITICO: Un solo stabilimento produttivo")
        suggestions.append("Identificare e qualificare second source")
        weeks_qual = _get_safe_value(row, 'Weeks to qualify', 12)
        if weeks_qual:
            man_hours += int(weeks_qual) * 40
        else:
            man_hours += 200
    elif num_plants == 2:
        score += 10
        factors.append("🏭 MEDIO: Solo 2 stabilimenti produttivi")

    # =====================================================================
    # 3. RISCHIO LEAD TIME (15%)
    # =====================================================================
    lead_time = _get_safe_value(row, 'Supplier Lead Time (weeks)', 0)
    if lead_time is not None:
        try:
            lead_time = int(float(lead_time))
            if lead_time > LEAD_TIME_THRESHOLDS['critical']:
                score += 15
                factors.append(f"⏱️ CRITICO: Lead time molto lungo ({lead_time} settimane)")
                suggestions.append("Negoziare rolling forecast o VMI con il fornitore")
                man_hours += 16
            elif lead_time > LEAD_TIME_THRESHOLDS['high']:
                score += 10
                factors.append(f"⏱️ ALTO: Lead time lungo ({lead_time} settimane)")
                suggestions.append("Implementare rolling forecast")
                man_hours += 8
            elif lead_time > LEAD_TIME_THRESHOLDS['medium']:
                score += 5
                factors.append(f"⏱️ MEDIO: Lead time moderato ({lead_time} settimane)")
        except (ValueError, TypeError):
            pass

    # =====================================================================
    # 4. RISCHIO BUFFER STOCK (15%) - con riduzione proporzionale
    # =====================================================================
    buffer_stock = _get_safe_value(row, 'If Dedicated Buffer Stock Units to the supplier is yes specify the number of Units', 0)
    qty_per_bom = _get_safe_value(row, 'How Many Device of this specific PN are in the BOM?', 1)

    buffer_coverage_weeks = 0
    if buffer_stock is not None and qty_per_bom is not None and lead_time is not None:
        try:
            buffer_stock = float(buffer_stock)
            qty_per_bom = float(qty_per_bom) if float(qty_per_bom) > 0 else 1
            weekly_consumption = run_rate * qty_per_bom

            if weekly_consumption > 0:
                buffer_coverage_weeks = buffer_stock / weekly_consumption

                if buffer_coverage_weeks < lead_time:
                    score += 15
                    factors.append(f"📦 CRITICO: Buffer copre solo {buffer_coverage_weeks:.1f} settimane (lead time: {lead_time})")
                    suggestions.append(f"Aumentare buffer stock ad almeno {lead_time * 1.5:.0f} settimane di copertura")
                    man_hours += 8
                elif buffer_coverage_weeks < lead_time * 1.5:
                    score += 8
                    factors.append(f"📦 MEDIO: Buffer copre {buffer_coverage_weeks:.1f} settimane")
                elif buffer_coverage_weeks >= lead_time * 2:
                    # Buffer molto ampio -> riduzione rischio proporzionale
                    buffer_bonus = min(5, int((buffer_coverage_weeks / lead_time - 2) * 2))
                    score = max(0, score - buffer_bonus)
                    if buffer_bonus > 0:
                        factors.append(f"📦 MITIGATO: Buffer ampio ({buffer_coverage_weeks:.1f} settimane, {buffer_coverage_weeks/lead_time:.1f}x lead time) - riduzione {buffer_bonus} punti")
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    # =====================================================================
    # 5. RISCHIO DIPENDENZE (10%)
    # =====================================================================
    standalone = _get_safe_value(row, 'Stand-Alone Functional Device (Y/N)', 'Y')
    if standalone and str(standalone).upper() == 'N':
        score += 10
        dependency = _get_safe_value(row, 'In case answer on Column C is Y, Which other device in the BOM is necessary to run the PN on Column B? (e.g. PMIC for MPU, Memory for MPU)', '')
        if dependency:
            factors.append(f"🔗 ALTO: Dipende da altri componenti ({dependency})")
        else:
            factors.append("🔗 ALTO: Dipende da altri componenti nella BOM")
        suggestions.append("Verificare allineamento rischio con componenti dipendenti")

    # =====================================================================
    # 6. RISCHIO PROPRIETARY (10%)
    # =====================================================================
    proprietary = _get_safe_value(row, 'Proprietary (Y/N)**', 'N')
    commodity = _get_safe_value(row, 'Commodity (Y/N)*', 'Y')

    if proprietary and str(proprietary).upper() == 'Y':
        score += 10
        factors.append("🔒 ALTO: Componente proprietario (no alternative dirette)")
        suggestions.append("Avviare studio di redesign con componente commodity/standard")
        man_hours += 200
    elif commodity and str(commodity).upper() == 'N':
        score += 5
        factors.append("🔒 MEDIO: Componente non-commodity")

    # =====================================================================
    # 7. RISCHIO CERTIFICAZIONI (5%)
    # =====================================================================
    weeks_qualify = _get_safe_value(row, 'Weeks to qualify', 0)
    certification = _get_safe_value(row, 'Specify Certification/Qualification', '')

    if weeks_qualify is not None:
        try:
            if int(weeks_qualify) > 12:
                score += 5
                cert_suffix = f" - {certification}" if certification else ""
                factors.append(f"📋 MEDIO: Riqualifica lunga ({int(weeks_qualify)} settimane){cert_suffix}")
                suggestions.append("Pre-qualificare alternative prima di potenziale EOL")
                man_hours += 16
        except (ValueError, TypeError):
            pass

    # =====================================================================
    # SWITCHING COST (informativo, non modifica lo score)
    # =====================================================================
    switching = calculate_switching_cost(row)

    # =====================================================================
    # 8. RISCHIO EOL STATUS (fino a +15 punti)
    # =====================================================================
    eol_status = str(_get_safe_value(row, 'EOL_Status', 'Active')).strip().upper()
    eol_scores = {
        'OBSOLETE': 15, 'EOL': 15, 'LAST_BUY': 12, 'LAST BUY': 12,
        'NRND': 8, 'NOT RECOMMENDED': 8, 'ACTIVE': 0,
    }
    eol_add = eol_scores.get(eol_status, 0)
    if eol_add > 0:
        score += eol_add
        if eol_add >= 12:
            factors.append(f"⚠️ CRITICO: Componente {eol_status} - fine vita o last buy")
            suggestions.append("Avviare urgentemente ricerca alternativa e last-time buy")
            man_hours += 80
        else:
            factors.append(f"⚠️ ALTO: Componente {eol_status} - non raccomandato per nuovi design")
            suggestions.append("Pianificare migrazione a componente attivo")
            man_hours += 40

    # =====================================================================
    # 9. RISCHIO ALTERNATIVE SOURCES (fino a +10 / bonus -3)
    # =====================================================================
    alt_sources = _get_safe_value(row, 'Number_of_Alternative_Sources', '')
    if alt_sources is not None and str(alt_sources).strip() != '':
        try:
            alt_sources_n = int(float(alt_sources))
            if alt_sources_n == 0:
                score += 10
                factors.append("🚫 CRITICO: Nessuna fonte alternativa sul mercato (sole source)")
                suggestions.append("Avviare redesign con componente multi-source")
                man_hours += 120
            elif alt_sources_n == 1:
                score += 5
                factors.append("🚫 ALTO: Solo 1 fonte alternativa disponibile")
                suggestions.append("Qualificare la fonte alternativa come second source")
                man_hours += 24
            elif alt_sources_n >= 3:
                bonus = min(3, alt_sources_n - 2)
                score = max(0, score - bonus)
                factors.append(f"✅ MITIGATO: {alt_sources_n} fonti alternative disponibili (-{bonus} punti)")
        except (ValueError, TypeError):
            pass

    # =====================================================================
    # 10. RISCHIO SALUTE FINANZIARIA FORNITORE (fino a +8)
    # =====================================================================
    fin_health = str(_get_safe_value(row, 'Supplier_Financial_Health', 'A')).strip().upper()
    fin_scores = {'A': 0, 'B': 2, 'C': 5, 'D': 8}
    fin_add = fin_scores.get(fin_health, 0)
    if fin_add > 0:
        score += fin_add
        if fin_add >= 5:
            factors.append(f"💰 ALTO: Salute finanziaria fornitore rating {fin_health}")
            suggestions.append("Monitorare rischio insolvenza/acquisizione fornitore")
            man_hours += 16
        else:
            factors.append(f"💰 MEDIO: Salute finanziaria fornitore rating {fin_health}")

    # =====================================================================
    # 11. RISCHIO ALLOCATION STATUS (fino a +10)
    # =====================================================================
    alloc_status = str(_get_safe_value(row, 'Allocation_Status', 'Normal')).strip().upper()
    alloc_scores = {'NORMAL': 0, 'CONSTRAINED': 5, 'ALLOCATED': 10}
    alloc_add = alloc_scores.get(alloc_status, 0)
    if alloc_add > 0:
        score += alloc_add
        if alloc_add >= 10:
            factors.append("📉 CRITICO: Componente in allocazione - forniture limitate")
            suggestions.append("Negoziare volumi garantiti e cercare broker affidabili")
            man_hours += 24
        else:
            factors.append("📉 ALTO: Componente con fornitura vincolata (constrained)")
            suggestions.append("Aumentare buffer stock e attivare monitoraggio lead time")
            man_hours += 8

    # =====================================================================
    # 12. RISCHIO AUMENTO PREZZO (fino a +5)
    # =====================================================================
    price_increase = _get_safe_value(row, 'Last_Price_Increase_Pct', 0)
    if price_increase is not None and str(price_increase).strip() != '':
        try:
            price_increase_f = float(price_increase)
            if price_increase_f > 50:
                score += 5
                factors.append(f"💲 ALTO: Ultimo aumento prezzo {price_increase_f:.0f}% - segnale di tensione supply")
                suggestions.append("Valutare alternative per contenere costi e ridurre dipendenza")
                man_hours += 8
            elif price_increase_f > 20:
                score += 3
                factors.append(f"💲 MEDIO: Ultimo aumento prezzo {price_increase_f:.0f}%")
        except (ValueError, TypeError):
            pass

    # =====================================================================
    # 13. RISCHIO PACKAGE TYPE (fino a +3)
    # =====================================================================
    package = str(_get_safe_value(row, 'Package_Type', '')).strip().upper()
    advanced_packages = ['WLCSP', 'FCCSP', 'FCBGA', 'FOWLP', 'CHIPLET', '2.5D', '3D']
    if package and any(ap in package for ap in advanced_packages):
        score += 3
        factors.append(f"📦 MEDIO: Package avanzato ({package}) - poche fonderie capaci")
        suggestions.append("Verificare disponibilita' capacity nelle fonderie qualificate")

    # =====================================================================
    # 14. MTBF e AUTOMOTIVE GRADE (informativi)
    # =====================================================================
    mtbf = _get_safe_value(row, 'MTBF_Hours', '')
    auto_grade = str(_get_safe_value(row, 'Automotive_Grade', '')).strip()
    if auto_grade and auto_grade.upper() not in ('', 'NONE', 'N/A'):
        factors.append(f"🚗 INFO: Grado automotive {auto_grade} - supply chain piu' rigida")
    if mtbf and str(mtbf).strip() != '':
        try:
            mtbf_val = float(mtbf)
            if mtbf_val < 50000:
                factors.append(f"⏳ INFO: MTBF basso ({mtbf_val:.0f}h) - possibile rischio affidabilita'")
        except (ValueError, TypeError):
            pass

    # Cap score a 100
    score = min(100, score)

    # Determina colore rischio
    if score >= RISK_THRESHOLDS['high']:
        color = "RED"
        risk_level = "ALTO"
    elif score >= RISK_THRESHOLDS['medium']:
        color = "YELLOW"
        risk_level = "MEDIO"
    else:
        color = "GREEN"
        risk_level = "BASSO"

    return {
        'score': score,
        'color': color,
        'risk_level': risk_level,
        'factors': factors,
        'suggestions': suggestions,
        'man_hours': man_hours,
        # v3.0 - Dati arricchiti
        'geo_risk': geo,
        'tech_node_risk': tech_node,
        'switching_cost': switching,
        'buffer_coverage_weeks': round(buffer_coverage_weeks, 1),
    }


# =============================================================================
# CALCOLO RISCHIO BOM (v2 legacy + v3 con dependency graph)
# =============================================================================

def calculate_bom_risk(components_risk: List[Dict[str, Any]], df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Calcola il rischio complessivo della BOM pesato per valore.
    Retrocompatibile con v2.
    """
    if not components_risk:
        return {'score': 0, 'color': 'GREEN', 'risk_level': 'N/A'}

    total_value = 0
    weighted_score = 0

    if df is not None:
        for i, risk in enumerate(components_risk):
            if i < len(df):
                price = _get_safe_value(df.iloc[i], 'Unit Price ($)', 1)
                qty = _get_safe_value(df.iloc[i], 'How Many Device of this specific PN are in the BOM?', 1)

                price = float(price) if price is not None else 1
                qty = float(qty) if qty is not None else 1

                value = price * qty
                total_value += value
                weighted_score += risk['score'] * value

        if total_value > 0:
            avg_score = weighted_score / total_value
        else:
            avg_score = sum(r['score'] for r in components_risk) / len(components_risk)
    else:
        avg_score = sum(r['score'] for r in components_risk) / len(components_risk)

    if avg_score >= RISK_THRESHOLDS['high']:
        return {'score': avg_score, 'color': 'RED', 'risk_level': 'ALTO'}
    elif avg_score >= RISK_THRESHOLDS['medium']:
        return {'score': avg_score, 'color': 'YELLOW', 'risk_level': 'MEDIO'}
    else:
        return {'score': avg_score, 'color': 'GREEN', 'risk_level': 'BASSO'}


def calculate_bom_risk_v3(
    components: List[Dict[str, Any]],
    components_risk: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Calcolo rischio BOM v3 con dependency graph e chain risk propagation.

    Args:
        components: Lista dei dati dei componenti (per costruire il grafo)
        components_risk: Lista dei rischi calcolati per ogni componente

    Returns:
        Dizionario con:
            - score, color, risk_level: rischio BOM complessivo
            - dependency_graph: grafo Mermaid delle dipendenze
            - chain_risks: rischi propagati per catena
            - spofs: Single Points of Failure
            - max_chain_score: score peggiore nella catena
    """
    if not components_risk:
        return {
            'score': 0, 'color': 'GREEN', 'risk_level': 'N/A',
            'dependency_graph': None,
            'dependency_graph_mermaid': '', 'chain_risks': {}, 'spofs': [],
            'max_chain_score': 0,
        }

    # Costruisci grafo dipendenze
    graph = build_dependency_graph(components)

    # Mappa rischi per part number
    risk_by_pn = {}
    for i, comp in enumerate(components):
        pn = str(comp.get('Part Number', '') or comp.get('Supplier Part Number', f'PN_{i}'))
        if i < len(components_risk):
            risk_by_pn[pn] = components_risk[i]

    # Calcola chain risks
    chain_risks = calculate_chain_risk(graph, risk_by_pn)

    # Trova SPOF
    spofs = find_single_points_of_failure(graph)

    # Genera Mermaid
    mermaid = render_dependency_tree(graph, risk_by_pn)

    # Score BOM: media pesata per VALORE FINANZIARIO con chain scores
    all_scores = []
    all_values = []
    for i, risk in enumerate(components_risk):
        pn = str(components[i].get('Part Number', '')) if i < len(components) else ''
        chain = chain_risks.get(pn, {})
        # Usa il chain_score (peggiore tra individuale e catena) se disponibile
        effective_score = chain.get('chain_score', risk['score'])
        all_scores.append(effective_score)

        # Valore finanziario = unit_price * qty_in_bom
        if i < len(components):
            price = _get_safe_value(components[i], 'Unit Price ($)', 0)
            qty = _get_safe_value(components[i], 'How Many Device of this specific PN are in the BOM?', 1)
            try:
                price = float(price) if price else 0
                qty = float(qty) if qty and float(qty) > 0 else 1
            except (ValueError, TypeError):
                price, qty = 0, 1
            all_values.append(price * qty)
        else:
            all_values.append(0)

    # Media pesata per valore finanziario (fallback a media semplice se nessun prezzo)
    total_value = sum(all_values)
    if total_value > 0:
        weighted_score = sum(s * v for s, v in zip(all_scores, all_values)) / total_value
    else:
        weighted_score = sum(all_scores) / len(all_scores) if all_scores else 0

    # Media semplice (non pesata) per confronto
    simple_avg = sum(all_scores) / len(all_scores) if all_scores else 0
    max_chain = max(all_scores) if all_scores else 0

    # Usa lo score pesato come score BOM principale
    avg_score = weighted_score

    if avg_score >= RISK_THRESHOLDS['high']:
        color, risk_level = 'RED', 'ALTO'
    elif avg_score >= RISK_THRESHOLDS['medium']:
        color, risk_level = 'YELLOW', 'MEDIO'
    else:
        color, risk_level = 'GREEN', 'BASSO'

    return {
        'score': round(avg_score, 1),
        'color': color,
        'risk_level': risk_level,
        'dependency_graph': graph,
        'dependency_graph_mermaid': mermaid,
        'chain_risks': chain_risks,
        'spofs': spofs,
        'max_chain_score': max_chain,
        # v3.1 - Dettaglio peso finanziario
        'simple_avg_score': round(simple_avg, 1),
        'weighted_avg_score': round(weighted_score, 1),
        'total_bom_value': round(total_value, 2),
        'component_values': all_values,
    }
