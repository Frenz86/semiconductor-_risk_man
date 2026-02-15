"""
Tier-2/3 Supply Chain Visibility Module
========================================
Modulo per la visibilita' delle dipendenze a monte dei fornitori Tier-1.
Identifica materiali critici (gas, wafer, chimici, substrati) e la
concentrazione geografica dei fornitori Tier-2/3.

Approccio ibrido: mappature predefinite basate su categoria/nodo tecnologico
+ possibilita' di personalizzare con dati specifici.

Uso:
    from tier2_visibility import calculate_tier2_risk, analyze_bom_tier2_bottlenecks
"""

import pandas as pd
from typing import Dict, List, Any, Optional

# =============================================================================
# CONFIGURAZIONE - DATABASE MATERIALI CRITICI
# =============================================================================

MATERIAL_DATABASE = {
    'neon_gas': {
        'name': 'Neon Gas (Litografia)',
        'category': 'Specialty Gas',
        'primary_countries': {
            'ukraine': 0.40, 'russia': 0.30, 'korea': 0.15,
            'japan': 0.10, 'usa': 0.05
        },
        'primary_suppliers': ['Iceblick (UA)', 'Cryoin (UA)', 'Air Liquide', 'Linde'],
        'concentration_risk': 0.70,
        'criticality': 'CRITICAL',
        'substitutability': 'LOW',
        'affected_process': 'Lithography (EUV/DUV)',
    },
    'silicon_wafers': {
        'name': 'Silicon Wafers',
        'category': 'Substrate',
        'primary_countries': {
            'japan': 0.55, 'korea': 0.15, 'germany': 0.12,
            'taiwan': 0.10, 'usa': 0.08
        },
        'primary_suppliers': ['Shin-Etsu (JP)', 'SUMCO (JP)', 'Siltronic (DE)', 'SK Siltron (KR)', 'GlobalWafers (TW)'],
        'concentration_risk': 0.55,
        'criticality': 'CRITICAL',
        'substitutability': 'LOW',
        'affected_process': 'Wafer fabrication',
    },
    'photoresists': {
        'name': 'Photoresists',
        'category': 'Chemical',
        'primary_countries': {
            'japan': 0.90, 'usa': 0.05, 'germany': 0.05
        },
        'primary_suppliers': ['JSR (JP)', 'Tokyo Ohka Kogyo (JP)', 'Shin-Etsu Chemical (JP)', 'Fujifilm (JP)'],
        'concentration_risk': 0.90,
        'criticality': 'CRITICAL',
        'substitutability': 'VERY_LOW',
        'affected_process': 'Photolithography patterning',
    },
    'rare_earth_elements': {
        'name': 'Rare Earth Elements (REE)',
        'category': 'Raw Material',
        'primary_countries': {
            'china': 0.70, 'myanmar': 0.10, 'australia': 0.08,
            'usa': 0.05, 'others': 0.07
        },
        'primary_suppliers': ['China Northern RE (CN)', 'Lynas (AU)', 'MP Materials (US)'],
        'concentration_risk': 0.70,
        'criticality': 'HIGH',
        'substitutability': 'LOW',
        'affected_process': 'Magnets, phosphors, polishing',
    },
    'specialty_gases': {
        'name': 'Specialty Gases (F2, SiH4, PH3, AsH3)',
        'category': 'Specialty Gas',
        'primary_countries': {
            'usa': 0.30, 'japan': 0.25, 'korea': 0.20,
            'germany': 0.15, 'china': 0.10
        },
        'primary_suppliers': ['Air Liquide', 'Linde', 'Air Products', 'Showa Denko (JP)'],
        'concentration_risk': 0.30,
        'criticality': 'HIGH',
        'substitutability': 'MEDIUM',
        'affected_process': 'Etching, doping, deposition',
    },
    'sic_substrates': {
        'name': 'SiC Substrates',
        'category': 'Substrate',
        'primary_countries': {
            'usa': 0.60, 'china': 0.20, 'japan': 0.10, 'europe': 0.10
        },
        'primary_suppliers': ['Wolfspeed (US)', 'Coherent (US)', 'SICC (CN)', 'Resonac (JP)'],
        'concentration_risk': 0.60,
        'criticality': 'HIGH',
        'substitutability': 'LOW',
        'affected_process': 'Power semiconductor fabrication',
    },
    'gan_substrates': {
        'name': 'GaN Substrates/Epitaxy',
        'category': 'Substrate',
        'primary_countries': {
            'japan': 0.40, 'usa': 0.30, 'china': 0.15, 'europe': 0.15
        },
        'primary_suppliers': ['Sumitomo (JP)', 'Mitsubishi Chemical (JP)', 'IQE (UK)', 'AWSC (TW)'],
        'concentration_risk': 0.40,
        'criticality': 'HIGH',
        'substitutability': 'LOW',
        'affected_process': 'RF/Power GaN device fabrication',
    },
    'bonding_wire_gold': {
        'name': 'Gold Bonding Wire',
        'category': 'Packaging Material',
        'primary_countries': {
            'japan': 0.35, 'korea': 0.25, 'china': 0.20,
            'singapore': 0.10, 'europe': 0.10
        },
        'primary_suppliers': ['Heraeus (DE)', 'Tanaka (JP)', 'MK Electron (KR)', 'Nippon Micrometal (JP)'],
        'concentration_risk': 0.35,
        'criticality': 'MEDIUM',
        'substitutability': 'MEDIUM',
        'affected_process': 'Wire bonding (backend)',
    },
    'bonding_wire_palladium': {
        'name': 'Palladium-Coated Copper Wire',
        'category': 'Packaging Material',
        'primary_countries': {
            'south_africa': 0.40, 'russia': 0.25, 'canada': 0.10,
            'usa': 0.10, 'others': 0.15
        },
        'primary_suppliers': ['Heraeus (DE)', 'Tanaka (JP)', 'Nippon Micrometal (JP)'],
        'concentration_risk': 0.65,
        'criticality': 'MEDIUM',
        'substitutability': 'LOW',
        'affected_process': 'Wire bonding (backend)',
    },
    'hf_chemicals': {
        'name': 'High-Purity HF & H2O2',
        'category': 'Chemical',
        'primary_countries': {
            'japan': 0.35, 'usa': 0.25, 'korea': 0.20,
            'china': 0.10, 'europe': 0.10
        },
        'primary_suppliers': ['Stella Chemifa (JP)', 'Solvay', 'BASF', 'Daikin (JP)'],
        'concentration_risk': 0.35,
        'criticality': 'HIGH',
        'substitutability': 'MEDIUM',
        'affected_process': 'Wafer cleaning, etching',
    },
    'sapphire_substrates': {
        'name': 'Sapphire Substrates',
        'category': 'Substrate',
        'primary_countries': {
            'china': 0.50, 'russia': 0.15, 'japan': 0.15,
            'usa': 0.10, 'europe': 0.10
        },
        'primary_suppliers': ['Rubicon (US)', 'Monocrystal (RU)', 'Crystalwise (TW)'],
        'concentration_risk': 0.50,
        'criticality': 'MEDIUM',
        'substitutability': 'MEDIUM',
        'affected_process': 'LED/Sensor substrate',
    },
    'cmp_slurry': {
        'name': 'CMP Slurry & Pads',
        'category': 'Chemical',
        'primary_countries': {
            'usa': 0.45, 'japan': 0.30, 'korea': 0.15, 'europe': 0.10
        },
        'primary_suppliers': ['CMC Materials (US)', 'Fujimi (JP)', 'DuPont/Versum (US)'],
        'concentration_risk': 0.45,
        'criticality': 'HIGH',
        'substitutability': 'LOW',
        'affected_process': 'Chemical Mechanical Polishing',
    },
    'lead_frames': {
        'name': 'Lead Frames',
        'category': 'Packaging Material',
        'primary_countries': {
            'japan': 0.30, 'china': 0.25, 'malaysia': 0.20,
            'korea': 0.15, 'europe': 0.10
        },
        'primary_suppliers': ['Mitsui High-tec (JP)', 'Shinko (JP)', 'ASM Pacific (HK)', 'HAESUNG DS (KR)'],
        'concentration_risk': 0.30,
        'criticality': 'MEDIUM',
        'substitutability': 'MEDIUM',
        'affected_process': 'Package assembly',
    },
}


# =============================================================================
# MAPPATURA CATEGORIA + TECH NODE -> MATERIALI RICHIESTI
# =============================================================================

CATEGORY_MATERIAL_MAPPINGS = {
    # MCU
    ('MCU', 'advanced'):    ['silicon_wafers', 'photoresists', 'neon_gas', 'specialty_gases', 'hf_chemicals', 'cmp_slurry', 'bonding_wire_gold', 'lead_frames'],
    ('MCU', 'mainstream'):  ['silicon_wafers', 'photoresists', 'neon_gas', 'specialty_gases', 'hf_chemicals', 'bonding_wire_gold', 'lead_frames'],
    ('MCU', 'mature'):      ['silicon_wafers', 'neon_gas', 'specialty_gases', 'hf_chemicals', 'lead_frames'],
    ('MCU', 'legacy'):      ['silicon_wafers', 'neon_gas', 'hf_chemicals', 'lead_frames'],

    # MPU
    ('MPU', 'advanced'):    ['silicon_wafers', 'photoresists', 'neon_gas', 'specialty_gases', 'hf_chemicals', 'cmp_slurry', 'rare_earth_elements', 'bonding_wire_gold'],
    ('MPU', 'mainstream'):  ['silicon_wafers', 'photoresists', 'neon_gas', 'specialty_gases', 'hf_chemicals', 'cmp_slurry', 'bonding_wire_gold'],
    ('MPU', 'mature'):      ['silicon_wafers', 'neon_gas', 'specialty_gases', 'hf_chemicals', 'bonding_wire_gold'],
    ('MPU', 'legacy'):      ['silicon_wafers', 'neon_gas', 'hf_chemicals'],

    # Sensor
    ('Sensor', 'advanced'): ['silicon_wafers', 'photoresists', 'neon_gas', 'specialty_gases', 'sapphire_substrates', 'bonding_wire_gold'],
    ('Sensor', 'mainstream'): ['silicon_wafers', 'neon_gas', 'specialty_gases', 'sapphire_substrates', 'lead_frames'],
    ('Sensor', 'mature'):   ['silicon_wafers', 'neon_gas', 'specialty_gases', 'lead_frames'],
    ('Sensor', 'legacy'):   ['silicon_wafers', 'neon_gas', 'lead_frames'],

    # Power
    ('Power', 'advanced'):  ['sic_substrates', 'gan_substrates', 'silicon_wafers', 'specialty_gases', 'bonding_wire_gold', 'bonding_wire_palladium', 'lead_frames'],
    ('Power', 'mainstream'): ['sic_substrates', 'silicon_wafers', 'specialty_gases', 'bonding_wire_gold', 'lead_frames'],
    ('Power', 'mature'):    ['silicon_wafers', 'specialty_gases', 'lead_frames'],
    ('Power', 'legacy'):    ['silicon_wafers', 'lead_frames'],

    # Analogic
    ('Analogic', 'advanced'): ['silicon_wafers', 'photoresists', 'neon_gas', 'specialty_gases', 'hf_chemicals', 'lead_frames'],
    ('Analogic', 'mainstream'): ['silicon_wafers', 'neon_gas', 'specialty_gases', 'hf_chemicals', 'lead_frames'],
    ('Analogic', 'mature'): ['silicon_wafers', 'neon_gas', 'specialty_gases', 'lead_frames'],
    ('Analogic', 'legacy'): ['silicon_wafers', 'neon_gas', 'lead_frames'],

    # Passive Component
    ('Passive Component', 'any'): ['rare_earth_elements', 'lead_frames'],

    # Transceiver Wireless
    ('Transceiver Wireless', 'advanced'): ['silicon_wafers', 'photoresists', 'neon_gas', 'gan_substrates', 'specialty_gases', 'bonding_wire_gold'],
    ('Transceiver Wireless', 'mainstream'): ['silicon_wafers', 'neon_gas', 'gan_substrates', 'specialty_gases', 'bonding_wire_gold'],
    ('Transceiver Wireless', 'mature'): ['silicon_wafers', 'neon_gas', 'specialty_gases', 'lead_frames'],
    ('Transceiver Wireless', 'legacy'): ['silicon_wafers', 'neon_gas', 'lead_frames'],
}

# Nome lungo della colonna categoria (usato in tutto il codebase)
CATEGORY_COLUMN = 'Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)'


# =============================================================================
# FUNZIONI DI UTILITA'
# =============================================================================

def _get_safe(row: Dict[str, Any], key: str, default: Any = '') -> Any:
    """Ottiene un valore in modo sicuro."""
    val = row.get(key, default)
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    return val


def _classify_tech_node(tech_node: Any) -> str:
    """
    Classifica un nodo tecnologico in bucket per il mapping materiali.
    Returns: 'advanced', 'mainstream', 'mature', 'legacy'
    """
    if not tech_node or (isinstance(tech_node, float) and pd.isna(tech_node)):
        return 'mature'  # Default conservativo

    node_str = str(tech_node).lower().strip()

    # Estrai il numero di nm
    nm_value = None
    for part in node_str.replace('nm', ' ').replace('um', ' ').split():
        try:
            nm_value = float(part)
            break
        except ValueError:
            continue

    if nm_value is None:
        return 'mature'

    # Conversione um -> nm
    if 'um' in node_str or nm_value < 1:
        nm_value = nm_value * 1000

    if nm_value <= 7:
        return 'advanced'
    elif nm_value <= 28:
        return 'mainstream'
    elif nm_value <= 90:
        return 'mature'
    else:
        return 'legacy'


def _get_materials_for_component(category: str, tech_node: str) -> List[str]:
    """
    Restituisce la lista di material_key per un componente
    basata su categoria + tech node.
    """
    cat = str(category).strip() if category else ''
    node_bucket = _classify_tech_node(tech_node)

    # Prova match esatto (categoria, bucket)
    materials = CATEGORY_MATERIAL_MAPPINGS.get((cat, node_bucket))
    if materials:
        return materials

    # Prova con bucket 'any' (es. Passive Component)
    materials = CATEGORY_MATERIAL_MAPPINGS.get((cat, 'any'))
    if materials:
        return materials

    # Fallback: cerca match parziale sulla categoria
    for (mapped_cat, mapped_bucket), mat_list in CATEGORY_MATERIAL_MAPPINGS.items():
        if mapped_cat.lower() in cat.lower() or cat.lower() in mapped_cat.lower():
            if mapped_bucket == node_bucket or mapped_bucket == 'any':
                return mat_list

    # Default minimo
    return ['silicon_wafers', 'lead_frames']


# =============================================================================
# CALCOLO RISCHIO TIER-2/3 PER SINGOLO COMPONENTE
# =============================================================================

def calculate_tier2_risk(
    component_data: Dict[str, Any],
    custom_tier2_data: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Calcola il rischio Tier-2/3 per un singolo componente.

    Args:
        component_data: Dizionario dal lookup (stessa struttura di risk_engine)
        custom_tier2_data: Lista opzionale di record custom da Component_Materials

    Returns:
        {
            'tier2_score': int (0-25),
            'materials': List[Dict],
            'bottlenecks': List[Dict],
            'concentration_risks': Dict,
            'custom_overrides_applied': bool,
            'suggestions': List[str],
            'factors': List[str],
        }
    """
    category = _get_safe(component_data, CATEGORY_COLUMN, '')
    tech_node = _get_safe(component_data, 'Technology_Node', '')
    frontend_country = _get_safe(component_data, 'Frontend_Country', '').lower()

    # Ottieni materiali richiesti
    material_keys = _get_materials_for_component(category, tech_node)

    # Se ci sono dati custom, integra/sovrascrivi
    custom_overrides = {}
    if custom_tier2_data:
        for custom in custom_tier2_data:
            mat_key = _get_safe(custom, 'Material_Key', '')
            if mat_key:
                custom_overrides[mat_key] = custom
                if mat_key not in material_keys:
                    material_keys.append(mat_key)

    # Analizza ogni materiale
    materials_info = []
    bottlenecks = []
    concentration_risks = {}
    max_country_share = 0.0
    critical_count = 0
    geo_overlap_score = 0

    for mat_key in material_keys:
        mat_data = MATERIAL_DATABASE.get(mat_key)
        if not mat_data:
            continue

        # Applica override custom se presente
        if mat_key in custom_overrides:
            custom = custom_overrides[mat_key]
            custom_conc = custom.get('Custom_Concentration')
            custom_country = _get_safe(custom, 'Custom_Country', '')
            if custom_conc is not None and not (isinstance(custom_conc, float) and pd.isna(custom_conc)):
                effective_concentration = float(custom_conc)
            else:
                effective_concentration = mat_data['concentration_risk']
            dominant_country = custom_country if custom_country else _get_dominant_country(mat_data)
        else:
            effective_concentration = mat_data['concentration_risk']
            dominant_country = _get_dominant_country(mat_data)

        # Traccia concentrazione massima
        max_single_country = max(mat_data['primary_countries'].values()) if mat_data['primary_countries'] else 0
        if max_single_country > max_country_share:
            max_country_share = max_single_country

        # Conta materiali critici
        if mat_data['criticality'] in ('CRITICAL',) or mat_data['substitutability'] == 'VERY_LOW':
            critical_count += 1

        # Controlla overlap geopolitico col frontend
        if frontend_country and frontend_country in mat_data['primary_countries']:
            share = mat_data['primary_countries'][frontend_country]
            if share >= 0.20:
                geo_overlap_score += 1

        mat_info = {
            'key': mat_key,
            'name': mat_data['name'],
            'category': mat_data['category'],
            'concentration_risk': effective_concentration,
            'dominant_country': dominant_country,
            'criticality': mat_data['criticality'],
            'substitutability': mat_data['substitutability'],
            'suppliers': mat_data['primary_suppliers'],
            'affected_process': mat_data['affected_process'],
            'is_custom_override': mat_key in custom_overrides,
        }
        materials_info.append(mat_info)

        concentration_risks[mat_key] = {
            'name': mat_data['name'],
            'concentration': effective_concentration,
            'dominant_country': dominant_country,
        }

        # E' un bottleneck?
        if effective_concentration >= 0.50 or mat_data['criticality'] == 'CRITICAL':
            bottlenecks.append({
                'key': mat_key,
                'name': mat_data['name'],
                'category': mat_data['category'],
                'concentration': effective_concentration,
                'dominant_country': dominant_country,
                'criticality': mat_data['criticality'],
            })

    # =========================================================================
    # CALCOLO SCORE (0-25)
    # =========================================================================

    score = 0
    factors = []
    suggestions = []

    # 1. Concentrazione materiale (0-10)
    if max_country_share >= 0.80:
        score += 10
        factors.append(f"Concentrazione Tier-2 estrema: {max_country_share:.0%} da un singolo paese")
    elif max_country_share >= 0.60:
        score += 7
        factors.append(f"Concentrazione Tier-2 alta: {max_country_share:.0%} da un singolo paese")
    elif max_country_share >= 0.40:
        score += 4
        factors.append(f"Concentrazione Tier-2 moderata: {max_country_share:.0%} da un singolo paese")
    elif max_country_share >= 0.20:
        score += 2

    # 2. Numero materiali critici (0-5)
    if critical_count >= 3:
        score += 5
        factors.append(f"{critical_count} materiali critici/non-sostituibili")
    elif critical_count >= 2:
        score += 3
        factors.append(f"{critical_count} materiali critici")
    elif critical_count >= 1:
        score += 1

    # 3. Overlap geopolitico frontend/tier2 (0-5)
    if geo_overlap_score >= 3:
        score += 5
        factors.append("Alto overlap geo: frontend e Tier-2 nello stesso paese")
        suggestions.append("Diversificare fonti Tier-2 su paesi diversi dal frontend")
    elif geo_overlap_score >= 2:
        score += 3
        factors.append("Overlap geo: frontend e Tier-2 parzialmente sovrapposti")
    elif geo_overlap_score >= 1:
        score += 1

    # 4. Penalita' nodo avanzato (0-5)
    node_bucket = _classify_tech_node(tech_node)
    if node_bucket == 'advanced':
        score += 5
        factors.append("Nodo avanzato (<= 7nm): supply chain Tier-2 molto concentrata")
        suggestions.append("Valutare alternative su nodi maturi dove possibile")
    elif node_bucket == 'mainstream':
        score += 3
        factors.append("Nodo mainstream (10-28nm): buona disponibilita' Tier-2")
    elif node_bucket == 'mature':
        score += 1

    # Suggerimenti basati sui bottleneck
    for bn in sorted(bottlenecks, key=lambda x: x['concentration'], reverse=True)[:3]:
        if bn['concentration'] >= 0.70:
            suggestions.append(
                f"Qualificare fonte alternativa per {bn['name']} "
                f"(attualmente {bn['concentration']:.0%} da {bn['dominant_country'].title()})"
            )
        elif bn['concentration'] >= 0.50:
            suggestions.append(
                f"Monitorare disponibilita' {bn['name']} ({bn['dominant_country'].title()})"
            )

    return {
        'tier2_score': min(25, score),
        'materials': materials_info,
        'bottlenecks': sorted(bottlenecks, key=lambda x: x['concentration'], reverse=True),
        'concentration_risks': concentration_risks,
        'custom_overrides_applied': bool(custom_overrides),
        'suggestions': suggestions,
        'factors': factors,
        'node_bucket': node_bucket,
    }


def _get_dominant_country(mat_data: Dict[str, Any]) -> str:
    """Restituisce il paese dominante per un materiale."""
    countries = mat_data.get('primary_countries', {})
    if not countries:
        return 'unknown'
    return max(countries, key=countries.get)


# =============================================================================
# ANALISI BOTTLENECK A LIVELLO BOM
# =============================================================================

def analyze_bom_tier2_bottlenecks(
    components_list: List[Dict[str, Any]],
    custom_data_by_pn: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> Dict[str, Any]:
    """
    Analisi dei colli di bottiglia Tier-2 a livello BOM.

    Args:
        components_list: Lista di componenti dal lookup
        custom_data_by_pn: Dict {part_number: [custom_materials]} dal database

    Returns:
        {
            'material_frequency': Dict[str, int],
            'top_bottlenecks': List[Dict],
            'country_concentration': Dict[str, Dict],
            'heatmap_data': List[Dict],
            'bom_tier2_score': float,
            'component_tier2_risks': Dict[str, Dict],
            'recommendations': List[str],
        }
    """
    if not components_list:
        return {
            'material_frequency': {},
            'top_bottlenecks': [],
            'country_concentration': {},
            'heatmap_data': [],
            'bom_tier2_score': 0.0,
            'component_tier2_risks': {},
            'recommendations': [],
        }

    material_frequency = {}   # material_key -> count
    material_components = {}  # material_key -> [part_numbers]
    country_exposure = {}     # country -> {'materials': set, 'components': set, 'total_exposure': float}
    component_risks = {}      # pn -> tier2_risk result
    total_score = 0

    for comp in components_list:
        pn = _get_safe(comp, 'Part Number', '')
        custom_data = (custom_data_by_pn or {}).get(pn, None)

        tier2 = calculate_tier2_risk(comp, custom_data)
        component_risks[pn] = tier2
        total_score += tier2['tier2_score']

        for mat in tier2['materials']:
            mat_key = mat['key']

            # Frequenza materiale
            material_frequency[mat_key] = material_frequency.get(mat_key, 0) + 1
            if mat_key not in material_components:
                material_components[mat_key] = []
            material_components[mat_key].append(pn)

            # Concentrazione per paese
            mat_data = MATERIAL_DATABASE.get(mat_key, {})
            for country, share in mat_data.get('primary_countries', {}).items():
                if country not in country_exposure:
                    country_exposure[country] = {
                        'materials': set(),
                        'components': set(),
                        'total_exposure': 0.0,
                    }
                country_exposure[country]['materials'].add(mat_key)
                country_exposure[country]['components'].add(pn)
                country_exposure[country]['total_exposure'] += share

    # Costruisci top bottlenecks
    top_bottlenecks = []
    for mat_key, count in sorted(material_frequency.items(), key=lambda x: x[1], reverse=True):
        mat_data = MATERIAL_DATABASE.get(mat_key, {})
        if not mat_data:
            continue
        countries = mat_data.get('primary_countries', {})
        max_concentration = max(countries.values()) if countries else 0
        dominant_country = max(countries, key=countries.get) if countries else 'unknown'

        top_bottlenecks.append({
            'key': mat_key,
            'name': mat_data.get('name', mat_key),
            'category': mat_data.get('category', ''),
            'affected_count': count,
            'affected_pns': material_components.get(mat_key, []),
            'max_concentration': max_concentration,
            'dominant_country': dominant_country,
            'criticality': mat_data.get('criticality', 'MEDIUM'),
            'substitutability': mat_data.get('substitutability', 'MEDIUM'),
        })

    # Ordina per impatto (frequenza * concentrazione)
    top_bottlenecks.sort(
        key=lambda x: x['affected_count'] * x['max_concentration'],
        reverse=True
    )

    # Costruisci heatmap data
    heatmap_data = []
    all_countries = sorted(country_exposure.keys())
    all_materials = sorted(material_frequency.keys())
    for mat_key in all_materials:
        mat_data = MATERIAL_DATABASE.get(mat_key, {})
        mat_name = mat_data.get('name', mat_key)
        countries = mat_data.get('primary_countries', {})
        for country in all_countries:
            share = countries.get(country, 0)
            freq = material_frequency.get(mat_key, 0)
            heatmap_data.append({
                'Material': mat_name,
                'Country': country.title(),
                'Exposure': round(share * freq, 2),
            })

    # Serializza sets per country_concentration
    country_concentration_serialized = {}
    for country, data in country_exposure.items():
        country_concentration_serialized[country] = {
            'materials': list(data['materials']),
            'components': list(data['components']),
            'total_exposure': round(data['total_exposure'], 2),
            'material_count': len(data['materials']),
            'component_count': len(data['components']),
        }

    # Raccomandazioni
    recommendations = _generate_recommendations(
        top_bottlenecks, country_concentration_serialized, len(components_list)
    )

    bom_score = total_score / len(components_list) if components_list else 0

    return {
        'material_frequency': material_frequency,
        'top_bottlenecks': top_bottlenecks,
        'country_concentration': country_concentration_serialized,
        'heatmap_data': heatmap_data,
        'bom_tier2_score': round(bom_score, 1),
        'component_tier2_risks': component_risks,
        'recommendations': recommendations,
    }


def _generate_recommendations(
    bottlenecks: List[Dict],
    country_conc: Dict[str, Dict],
    total_components: int
) -> List[str]:
    """Genera raccomandazioni di mitigazione basate sull'analisi."""
    recs = []

    # Raccomandazioni basate sui bottleneck
    for bn in bottlenecks[:5]:
        pct = bn['affected_count'] / total_components * 100 if total_components > 0 else 0
        if bn['max_concentration'] >= 0.70 and pct >= 50:
            recs.append(
                f"**CRITICO**: {bn['name']} interessa {bn['affected_count']}/{total_components} componenti "
                f"({pct:.0f}%) con {bn['max_concentration']:.0%} concentrazione in "
                f"{bn['dominant_country'].title()}. Qualificare fornitore alternativo urgente."
            )
        elif bn['max_concentration'] >= 0.50 and pct >= 30:
            recs.append(
                f"**ALTO**: {bn['name']} impatta {bn['affected_count']} componenti con alta concentrazione "
                f"({bn['dominant_country'].title()} {bn['max_concentration']:.0%}). "
                f"Valutare dual-sourcing."
            )
        elif bn['criticality'] == 'CRITICAL':
            recs.append(
                f"**MEDIO**: {bn['name']} e' un materiale critico non facilmente sostituibile. "
                f"Monitorare disponibilita' e build buffer strategico."
            )

    # Raccomandazioni basate sulla concentrazione per paese
    for country, data in sorted(
        country_conc.items(),
        key=lambda x: x[1]['total_exposure'],
        reverse=True
    )[:3]:
        if data['component_count'] >= total_components * 0.5:
            recs.append(
                f"**GEOPOLITICO**: {country.title()} impatta {data['material_count']} materiali "
                f"e {data['component_count']} componenti. Una disruption in questo paese "
                f"avrebbe impatto sistemico sulla BOM."
            )

    if not recs:
        recs.append("Nessun rischio Tier-2/3 significativo identificato per questa BOM.")

    return recs


# =============================================================================
# LOOKUP PER WHAT-IF SIMULATOR
# =============================================================================

def get_components_by_material(
    material_key: str,
    components_list: List[Dict[str, Any]],
    custom_data_by_pn: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> List[str]:
    """
    Dato un material_key, restituisce i Part Number che ne dipendono.
    Usato dal What-If simulator per scenari material_shortage.
    """
    affected = []
    for comp in components_list:
        pn = _get_safe(comp, 'Part Number', '')
        category = _get_safe(comp, CATEGORY_COLUMN, '')
        tech_node = _get_safe(comp, 'Technology_Node', '')

        materials = _get_materials_for_component(category, tech_node)

        # Aggiungi materiali custom
        if custom_data_by_pn and pn in custom_data_by_pn:
            for custom in custom_data_by_pn[pn]:
                custom_key = _get_safe(custom, 'Material_Key', '')
                if custom_key and custom_key not in materials:
                    materials.append(custom_key)

        if material_key in materials:
            affected.append(pn)

    return affected


def get_components_by_material_country(
    country: str,
    components_list: List[Dict[str, Any]],
    custom_data_by_pn: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> Dict[str, List[str]]:
    """
    Dato un paese, restituisce {material_key: [part_numbers]} per tutti
    i materiali con sourcing significativo (>= 10%) da quel paese.
    """
    result = {}
    country_lower = country.lower().strip()

    for comp in components_list:
        pn = _get_safe(comp, 'Part Number', '')
        category = _get_safe(comp, CATEGORY_COLUMN, '')
        tech_node = _get_safe(comp, 'Technology_Node', '')

        materials = _get_materials_for_component(category, tech_node)

        for mat_key in materials:
            mat_data = MATERIAL_DATABASE.get(mat_key, {})
            countries = mat_data.get('primary_countries', {})
            share = countries.get(country_lower, 0)
            if share >= 0.10:
                if mat_key not in result:
                    result[mat_key] = []
                if pn not in result[mat_key]:
                    result[mat_key].append(pn)

    return result
