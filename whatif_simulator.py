"""
What-If Simulator - Simulazione Scenari di Disruption
====================================================
Modulo per simulare impatti di disruption sulla supply chain.

Permette di:
- Definire scenari di blocco geografico (es. Taiwan bloccato 8 settimane)
- Simulare aumento dei lead time
- Vedere l'impatto sul buffer stock e sul rischio
- Calcolare impatto finanziario (settimane di produzione perse)

Uso:
    from whatif_simulator import simulate_disruption, calculate_impact
    result = simulate_disruption(components, scenario_type, ...)
"""

import pandas as pd
from typing import Dict, List, Any
from datetime import datetime, timedelta

# =============================================================================
# CONFIGURAZIONE SCENARI
# =============================================================================


SCENARIO_TYPES = {
    'country_block': 'Blocco Paese',
    'supplier_outage': 'Interruzione Fornitore',
    'lead_time_increase': 'Aumento Lead Time',
    'demand_surge': 'Picco Domanda',
}

# Paesi a alto rischio con durate consigliate per blocco
COUNTRY_BLOCK_CONFIG = {
    'Taiwan': {'default_weeks': 8, 'risk_multiplier': 3.0},
    'China': {'default_weeks': 6, 'risk_multiplier': 2.5},
    'Korea': {'default_weeks': 4, 'risk_multiplier': 2.0},
    'Japan': {'default_weeks': 4, 'risk_multiplier': 1.8},
    'Malaysia': {'default_weeks': 3, 'risk_multiplier': 1.5},
    'Singapore': {'default_weeks': 3, 'risk_multiplier': 1.3},
    'Philippines': {'default_weeks': 3, 'risk_multiplier': 1.3},
}

# =============================================================================
# FUNZIONI DI SUPPORTO
# =============================================================================


def _get_safe(value, default=''):
    """Ottiene un valore in modo sicuro gestendo None e NaN."""
    if value is None:
        return default
    if isinstance(value, float) and pd.isna(value):
        return default
    return value


def _is_component_affected(component: Dict[str, Any], scenario: Dict[str, Any]) -> bool:
    """
    Verifica se un componente è affetto dallo scenario.

    Args:
        component: Dati del componente
        scenario: Dizionario con parametri dello scenario

    Returns:
        True se il componente è affetto, False altrimenti
    """
    scenario_type = scenario.get('type', '')

    if scenario_type == 'country_block':
        # Controlla se frontend o backend country corrisponde al paese bloccato
        blocked_country = str(_get_safe(scenario.get('country', ''))).lower().strip()

        pn = component.get('Part Number', 'UNKNOWN')

        # Debug: mostra TUTTI i campi disponibili nel componente la prima volta
        if pn == 'UNKNOWN' or not hasattr(_is_component_affected, '_debug_done'):
            print(f"\n[COUNTRY_BLOCK DEBUG] Campi disponibili in componente {pn}:")
            for key in sorted(component.keys()):
                if 'country' in key.lower() or 'plant' in key.lower() or 'ems' in key.lower():
                    print(f"  {key}: {component.get(key)}")
            _is_component_affected._debug_done = True

        # Prova diversi nomi di colonna per Frontend/Backend
        frontend = str(_get_safe(
            component.get('Frontend_Country')
            or component.get('frontend_country')
            or component.get('Country of Manufacturing Plant 1')
            or ''
        )).lower().strip()

        backend = str(_get_safe(
            component.get('Backend_Country')
            or component.get('backend_country')
            or component.get('EMS_Location')
            or ''
        )).lower().strip()

        # Debug: stampa per verificare i valori
        print(f"[COUNTRY_BLOCK] PN: {pn}, Blocked: '{blocked_country}', Frontend: '{frontend}', Backend: '{backend}'")

        result = frontend == blocked_country or backend == blocked_country
        print(f"  -> Result: {result}")
        return result

    elif scenario_type == 'supplier_outage':
        # Controlla se il fornitore corrisponde
        blocked_supplier = str(_get_safe(scenario.get('supplier', ''))).lower()
        component_supplier = str(_get_safe(component.get('Supplier Name', ''))).lower()
        return blocked_supplier in component_supplier

    elif scenario_type == 'lead_time_increase':
        # Tutti i componenti sono affetti (aumento globale lead time)
        return True

    elif scenario_type == 'demand_surge':
        # Tutti i componenti sono affetti (picco domanda)
        return True

    return False


# =============================================================================
# FUNZIONI DI CALCOLO IMPATTO
# =============================================================================


def calculate_buffer_depletion(
    component: Dict[str, Any],
    run_rate: int,
    disruption_weeks: int
) -> Dict[str, Any]:
    """
    Calcola quando il buffer stock si esaurisce.

    Args:
        component: Dati del componente
        run_rate: Tasso di produzione (PCB/settimana)
        disruption_weeks: Settimane di interruzione forniture

    Returns:
        Dizionario con settimane_rimanenti, data_esaurimento, is_critical
    """
    buffer_stock = float(_get_safe(
        component.get('If Dedicated Buffer Stock Units to supplier is yes specify number of Units', 0),
        0
    ))
    qty_per_bom = float(_get_safe(
        component.get('How Many Device of this specific PN are in BOM?', 1),
        1
    ))

    if buffer_stock <= 0:
        return {
            'buffer_weeks': 0,
            'remaining_weeks': 0,
            'depletion_date': None,
            'is_critical': True,
            'remaining': 0,
        }

    # Consumo settimanale del componente
    try:
        weekly_consumption = run_rate * qty_per_bom
    except (TypeError, ZeroDivisionError):
        weekly_consumption = run_rate

    if weekly_consumption <= 0:
        return {
            'buffer_weeks': 0,
            'remaining_weeks': 0,
            'depletion_date': None,
            'is_critical': True,
            'remaining': 0,
        }

    # Settimane di copertura attuali
    current_coverage = buffer_stock / weekly_consumption

    # Settimane rimanenti dopo la disruption
    remaining_weeks = max(0, current_coverage - disruption_weeks)
    remaining_buffer = remaining_weeks * weekly_consumption

    # Data di esaurimento
    start_date = datetime.now()
    depletion_date = start_date + timedelta(weeks=disruption_weeks) if remaining_weeks > 0 else start_date

    return {
        'buffer_weeks': round(current_coverage, 1),
        'remaining_weeks': round(remaining_weeks, 1),
        'depletion_date': depletion_date.strftime('%Y-%m-%d') if remaining_weeks <= 0 else None,
        'is_critical': remaining_weeks <= 0,
        'remaining': round(remaining_buffer, 0),
    }


def calculate_adjusted_risk_score(
    original_score: int,
    original_buffer_weeks: float,
    new_buffer_weeks: float,
    component: Dict[str, Any],
    scenario: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calcola il punteggio di rischio aggiustato in base allo scenario.

    Args:
        original_score: Score originale del componente
        original_buffer_weeks: Settimane di copertura buffer originali
        new_buffer_weeks: Settimane di copertura dopo lo scenario
        component: Dati del componente (per recupero lead time originale)
        scenario: Parametri dello scenario

    Returns:
        Dizionario con adjusted_score, change, reason
    """
    scenario_type = scenario.get('type', '')

    # Fattore di aumento base sul tipo di scenario
    if scenario_type == 'country_block':
        # Aumento drastico del rischio per blocco paese
        risk_multiplier = scenario.get('risk_multiplier', 2.0)
        base_increase = original_score * (risk_multiplier - 1)

        # Se il buffer è insufficiente, penalità extra
        buffer_penalty = 0
        if new_buffer_weeks < original_buffer_weeks * 0.5:
            buffer_penalty = min(15, (original_buffer_weeks - new_buffer_weeks) * 2)

        adjusted = min(100, original_score + base_increase + buffer_penalty)

    elif scenario_type == 'lead_time_increase':
        # Aumento proporzionale al lead time
        increase_percent = scenario.get('increase_percent', 50)
        lead_factor = 1 + (increase_percent / 100)

        # Aggiorna punteggio fattore lead time (15% del totale)
        original_lead_score = min(15, original_score * 0.15)  # Assumiamo che parte del score venga da lead time
        new_lead_score = original_lead_score * lead_factor

        adjusted = original_score - original_lead_score + new_lead_score

    else:  # supplier_outage, demand_surge, altri
        adjusted = original_score

    change = adjusted - original_score

    # Determina livello di rischio aggiustato
    if adjusted >= 55:
        new_color = 'RED'
        new_level = 'ALTO'
    elif adjusted >= 30:
        new_color = 'YELLOW'
        new_level = 'MEDIO'
    else:
        new_color = 'GREEN'
        new_level = 'BASSO'

    return {
        'adjusted_score': round(adjusted, 1),
        'change': round(change, 1),
        'new_color': new_color,
        'new_level': new_level,
        'reason': f"{scenario.get('description', 'Scenario')} - {SCENARIO_TYPES.get(scenario_type, scenario_type)}",
    }


# =============================================================================
# FUNZIONE PRINCIPALE DI SIMULAZIONE
# =============================================================================


def simulate_disruption(
    components: List[Dict[str, Any]],
    components_risk: List[Dict[str, Any]],
    scenario: Dict[str, Any],
    run_rate: int
) -> Dict[str, Any]:
    """
    Simula l'impatto di uno scenario di disruption sulla BOM.

    Args:
        components: Lista dati componenti
        components_risk: Lista rischi calcolati
        scenario: Dizionario con:
            - type: 'country_block', 'supplier_outage', 'lead_time_increase', 'demand_surge'
            - country: Paese bloccato (per country_block)
            - supplier: Fornitore interrotto (per supplier_outage)
            - weeks: Durata in settimane
            - increase_percent: Percentuale aumento lead time
            - description: Descrizione leggibile
        run_rate: Tasso di produzione attuale

    Returns:
        Dizionario con:
            - scenario_info: Info scenario
            - impacted_components: Componenti affetti e impatti
            - summary: Riepilogo risultati
            - financial_impact: Impatto finanziario
            - risk_change: Cambiamento rischio complessivo
            - critical_components: Componenti critici
    """
    scenario_type = scenario.get('type', '')
    description = scenario.get('description', 'Scenario di disruption')
    duration_weeks = scenario.get('weeks', 4)

    # Filtra componenti affetti
    impacted = []
    total_value_impact = 0
    total_production_lost = 0

    for i, comp in enumerate(components):
        if _is_component_affected(comp, scenario):
            risk = components_risk[i] if i < len(components_risk) else {'score': 0}
            original_score = risk.get('score', 0)
            original_buffer = risk.get('buffer_coverage_weeks', 0)

            # Calcola esaurimento buffer
            buffer_impact = calculate_buffer_depletion(comp, run_rate, duration_weeks)

            # Calcola rischio aggiustato
            risk_adjustment = calculate_adjusted_risk_score(
                original_score,
                original_buffer,
                buffer_impact['remaining_weeks'],
                comp,
                scenario
            )

            # Calcola impatto finanziario
            unit_price = float(_get_safe(comp.get('Unit Price ($)', 0), 0))
            qty_in_bom = float(_get_safe(comp.get('How Many Device of this specific PN are in BOM?', 1), 1))

            # Settimane di produzione perse (se buffer esaurito prima della fine disruption)
            weeks_lost = max(0, duration_weeks - buffer_impact['remaining_weeks'])
            production_lost = weeks_lost * run_rate * qty_in_bom

            component_value = unit_price * qty_in_bom
            financial_impact = weeks_lost * component_value

            impacted.append({
                'part_number': _get_safe(comp.get('Part Number', '')),
                'supplier': _get_safe(comp.get('Supplier Name', 'N/A')),
                'original_score': original_score,
                'adjusted_score': risk_adjustment['adjusted_score'],
                'score_change': risk_adjustment['change'],
                'new_color': risk_adjustment['new_color'],
                'new_level': risk_adjustment['new_level'],
                'original_buffer_weeks': round(original_buffer, 1),
                'remaining_buffer_weeks': buffer_impact['remaining_weeks'],
                'depletion_date': buffer_impact['depletion_date'],
                'is_critical': buffer_impact['is_critical'],
                'weeks_lost': weeks_lost,
                'financial_impact': round(financial_impact, 2),
            })

            total_value_impact += component_value
            total_production_lost += production_lost

    # Calcola rischio complessivo aggiustato
    if impacted:
        avg_original = sum(c['original_score'] for c in impacted) / len(impacted)
        avg_adjusted = sum(c['adjusted_score'] for c in impacted) / len(impacted)
        risk_change = avg_adjusted - avg_original
    else:
        avg_original = 0
        avg_adjusted = 0
        risk_change = 0

    # Determina colore e livello complessivo
    if avg_adjusted >= 55:
        overall_color = 'RED'
        overall_level = 'ALTO'
    elif avg_adjusted >= 30:
        overall_color = 'YELLOW'
        overall_level = 'MEDIO'
    else:
        overall_color = 'GREEN'
        overall_level = 'BASSO'

    # Trova i componenti critici (si esaurisce subito)
    critical_components = [c for c in impacted if c['is_critical']]

    return {
        'scenario_info': {
            'type': SCENARIO_TYPES.get(scenario_type, scenario_type),
            'description': description,
            'duration_weeks': duration_weeks,
            'parameter': scenario.get('country', '')
                        or scenario.get('supplier', '')
                        or scenario.get('increase_percent', ''),
        },
        'impacted_components': impacted,
        'summary': {
            'total_components': len(components),
            'affected_count': len(impacted),
            'critical_count': len(critical_components),
            'avg_original_score': round(avg_original, 1),
            'avg_adjusted_score': round(avg_adjusted, 1),
            'score_change': round(risk_change, 1),
            'overall_color': overall_color,
            'overall_level': overall_level,
            'total_bom_value': round(total_value_impact, 2),
            'total_production_lost_weeks': round(total_production_lost / run_rate, 2) if run_rate else 0,
            'total_financial_impact': round(total_production_lost * 40, 2),
        },
        'financial_impact': {
            'total_value_at_risk': round(total_value_impact, 2),
            'production_lost_weeks': round(total_production_lost / run_rate, 2) if run_rate else 0,
            'estimated_revenue_loss': round(total_production_lost * 40, 2),
        },
        'risk_change': round(risk_change, 1),
        'critical_components': critical_components,
    }


# =============================================================================
# FUNZIONI HELPER PER UI
# =============================================================================


def get_predefined_scenarios() -> List[Dict[str, Any]]:
    """Restituisce scenari predefiniti per l'interfaccia."""
    return [
        {
            'name': 'Taiwan Block (8 settimane)',
            'type': 'country_block',
            'country': 'Taiwan',
            'weeks': 8,
            'description': 'Taiwan bloccata per 8 settimane - produzione wafer fermata',
            'risk_multiplier': 3.0,
        },
        {
            'name': 'Taiwan Block (4 settimane)',
            'type': 'country_block',
            'country': 'Taiwan',
            'weeks': 4,
            'description': 'Taiwan bloccata per 4 settimane - produzione wafer fermata',
            'risk_multiplier': 3.0,
        },
        {
            'name': 'China Block (6 settimane)',
            'type': 'country_block',
            'country': 'China',
            'weeks': 6,
            'description': 'Cina bloccata per 6 settimane - produzioni limitate',
            'risk_multiplier': 2.5,
        },
        {
            'name': 'Lead Time +50%',
            'type': 'lead_time_increase',
            'increase_percent': 50,
            'weeks': 4,
            'description': 'Aumento del 50% su tutti i lead time fornitori',
            'risk_multiplier': 1.5,
        },
        {
            'name': 'Lead Time +100%',
            'type': 'lead_time_increase',
            'increase_percent': 100,
            'weeks': 4,
            'description': 'Raddoppio dei lead time (100% - crisi globale)',
            'risk_multiplier': 2.0,
        },
    ]


def format_scenario_result(result: Dict[str, Any]) -> str:
    """Formatta risultato simulazione per display."""
    summary = result['summary']
    scenario = result['scenario_info']

    output = f"""
## Risultato Simulazione

**Scenario**: {scenario['description']} ({scenario['duration_weeks']} settimane)
**Parametro**: {scenario['parameter']}

### Riepilogo
- Componenti totali: {summary['total_components']}
- Componenti affetti: {summary['affected_count']} ({(summary['affected_count'] / summary['total_components'] * 100) if summary['total_components'] else 0:.1f}%)
- Componenti critici: {summary['critical_count']}

### Rischio Complessivo
- Score originale: {summary['avg_original_score']}
- Score aggiustato: {summary['avg_adjusted_score']}
- Variazione: {summary['score_change']:+.1f} punti
- Nuovo livello: {summary['overall_level']} ({summary['overall_color']})

### Impatto Finanziario
- Valore BOM a rischio: ${summary['total_bom_value']:,.2f}
- Produzione persa: {summary['total_production_lost_weeks']:.1f} settimane
- Impatto stimato: ${summary['total_financial_impact']:,.2f}
"""

    if result['critical_components']:
        output += "\n### Componenti Critici (Buffer esaurito)\n"
        for comp in result['critical_components'][:5]:
            output += f"- {comp['part_number']}: esaurisce in {comp['depletion_date'] or 'immediato'}\n"
        if len(result['critical_components']) > 5:
            output += f"... e altri {len(result['critical_components']) - 5} componenti\n"

    return output
