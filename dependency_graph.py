"""
Dependency Graph - Alberi di Correlazione Funzionale
====================================================
Modulo per la costruzione e analisi dei grafi di dipendenza
tra componenti elettronici nella BOM.

Identifica Single Points of Failure e propaga il rischio
lungo le catene funzionali (es. MPU ← PMIC, MPU ← DDR).

Uso:
    from dependency_graph import build_dependency_graph, calculate_chain_risk
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


# =============================================================================
# FUNZIONI DI UTILITÀ
# =============================================================================

def _get_safe(row: Dict[str, Any], key: str, default: Any = '') -> Any:
    """Ottiene un valore in modo sicuro."""
    val = row.get(key, default)
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    return val


def _match_dependency_target(dep_text: str, all_components: List[Dict[str, Any]]) -> List[str]:
    """
    Cerca i componenti target di una dipendenza nel testo.

    Il testo può contenere part number, nomi di supplier o categorie.
    Es: "STPMIC1APQR" oppure "PMIC for MPU" oppure "Memory"

    Returns:
        Lista di Part Number che matchano la dipendenza
    """
    if not dep_text:
        return []

    dep_lower = str(dep_text).lower().strip()
    matches = []

    for comp in all_components:
        pn = str(_get_safe(comp, 'Part Number', '')).lower()
        supplier = str(_get_safe(comp, 'Supplier Name', '')).lower()
        category = str(_get_safe(comp, 'Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)', '')).lower()

        # Match esatto per PN
        if pn and pn in dep_lower:
            matches.append(str(comp.get('Part Number', '')))
            continue

        # Match per categoria menzionata nel testo dipendenza
        # Es: "PMIC" nel testo -> match componenti Power/PMIC
        category_keywords = {
            'pmic': ['power', 'pmic'],
            'memory': ['memory', 'ddr', 'sdram', 'sram', 'flash'],
            'mpu': ['mpu'],
            'mcu': ['mcu'],
            'sensor': ['sensor'],
            'transceiver': ['transceiver', 'wireless', 'wifi', 'bluetooth'],
        }

        for keyword, cat_matches in category_keywords.items():
            if keyword in dep_lower:
                if any(cm in category for cm in cat_matches) or any(cm in pn for cm in cat_matches):
                    matches.append(str(comp.get('Part Number', '')))
                    break

    return list(set(matches))


# =============================================================================
# COSTRUZIONE GRAFO
# =============================================================================

def build_dependency_graph(components: List[Dict[str, Any]]) -> Optional[Any]:
    """
    Costruisce un grafo direzionale delle dipendenze tra componenti.

    Archi: componente_dipendente -> componente_da_cui_dipende
    Es: STM32MP157 -> STPMIC1 (l'MPU dipende dal PMIC)

    Args:
        components: Lista di dizionari con dati dei componenti

    Returns:
        networkx.DiGraph o None se networkx non disponibile
    """
    if not HAS_NETWORKX:
        return None

    G = nx.DiGraph()

    # Aggiungi tutti i componenti come nodi
    for comp in components:
        pn = str(_get_safe(comp, 'Part Number', ''))
        if not pn:
            continue

        standalone = str(_get_safe(comp, 'Stand-Alone Functional Device (Y/N)', 'Y')).upper()
        supplier = _get_safe(comp, 'Supplier Name', 'N/A')
        category = _get_safe(comp, 'Category of product (MCU, MPU, Sensor, Analogic, Power, Passive Component, Transceiver Wireless)', 'N/A')

        G.add_node(pn, **{
            'supplier': supplier,
            'category': category,
            'standalone': standalone == 'Y',
            'risk_score': 0,
            'risk_color': 'GREEN',
        })

    # Aggiungi archi per i componenti non-standalone
    for comp in components:
        pn = str(_get_safe(comp, 'Part Number', ''))
        standalone = str(_get_safe(comp, 'Stand-Alone Functional Device (Y/N)', 'Y')).upper()

        if standalone == 'N' and pn:
            dep_text = _get_safe(
                comp,
                'In case answer on Column C is Y, Which other device in the BOM is necessary to run the PN on Column B? (e.g. PMIC for MPU, Memory for MPU)',
                ''
            )

            if dep_text:
                targets = _match_dependency_target(dep_text, components)
                for target_pn in targets:
                    if target_pn != pn and G.has_node(target_pn):
                        G.add_edge(pn, target_pn, dependency_text=dep_text)

    return G


# =============================================================================
# ANALISI RISCHIO DI CATENA
# =============================================================================

def calculate_chain_risk(
    graph: Any,
    component_risks: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Calcola il rischio propagato lungo le catene di dipendenza.

    Logica: un componente non-standalone eredita il worst-case
    tra il suo rischio individuale e quello delle sue dipendenze.

    Args:
        graph: networkx.DiGraph dal build_dependency_graph
        component_risks: Dict {part_number: {score, color, risk_level, ...}}

    Returns:
        Dict {part_number: {chain_score, chain_color, chain_factors, pair_risks}}
    """
    if graph is None or not HAS_NETWORKX:
        return {}

    chain_risks = {}

    for node in graph.nodes():
        node_risk = component_risks.get(node, {'score': 0, 'color': 'GREEN', 'risk_level': 'BASSO'})
        own_score = node_risk.get('score', 0)

        # Trova tutte le dipendenze (dirette e transitive)
        try:
            dependencies = list(nx.descendants(graph, node))
        except nx.NetworkXError:
            dependencies = []

        # Predecessori: chi dipende da questo nodo
        try:
            dependents = list(nx.ancestors(graph, node))
        except nx.NetworkXError:
            dependents = []

        # Calcola worst-case tra le dipendenze
        dep_scores = []
        pair_risks = []

        for dep_pn in graph.successors(node):  # Dipendenze dirette
            dep_risk = component_risks.get(dep_pn, {'score': 0, 'color': 'GREEN', 'risk_level': 'BASSO'})
            dep_score = dep_risk.get('score', 0)
            dep_scores.append(dep_score)

            # Score di coppia
            pair_score = max(own_score, dep_score)
            pair_risks.append({
                'from': node,
                'to': dep_pn,
                'pair_score': pair_score,
                'pair_color': 'RED' if pair_score >= 55 else 'YELLOW' if pair_score >= 30 else 'GREEN',
            })

        # Chain score = max tra il proprio e tutte le dipendenze
        all_dep_scores = []
        for dep in dependencies:
            dr = component_risks.get(dep, {'score': 0})
            all_dep_scores.append(dr.get('score', 0))

        chain_score = max([own_score] + all_dep_scores) if all_dep_scores else own_score

        # Fattori di catena
        chain_factors = []
        if dep_scores and max(dep_scores) > own_score:
            worst_dep = max(dep_scores)
            chain_factors.append(
                f"Rischio ereditato da dipendenza (score catena: {chain_score} vs individuale: {own_score})"
            )
        if len(dependents) > 0:
            chain_factors.append(
                f"Componente critico: {len(dependents)} altri componenti dipendono da questo"
            )

        # Determina colore catena
        if chain_score >= 55:
            chain_color = 'RED'
            chain_level = 'ALTO'
        elif chain_score >= 30:
            chain_color = 'YELLOW'
            chain_level = 'MEDIO'
        else:
            chain_color = 'GREEN'
            chain_level = 'BASSO'

        chain_risks[node] = {
            'chain_score': chain_score,
            'own_score': own_score,
            'chain_color': chain_color,
            'chain_level': chain_level,
            'chain_factors': chain_factors,
            'pair_risks': pair_risks,
            'dependencies': list(graph.successors(node)),
            'dependents': list(graph.predecessors(node)),
            'is_standalone': graph.nodes[node].get('standalone', True),
        }

    return chain_risks


def find_single_points_of_failure(graph: Any) -> List[Dict[str, Any]]:
    """
    Identifica i Single Points of Failure nella BOM.

    Un SPOF è un componente la cui indisponibilità blocca altri componenti.

    Args:
        graph: networkx.DiGraph

    Returns:
        Lista di SPOF ordinata per impatto (numero di componenti bloccati)
    """
    if graph is None or not HAS_NETWORKX:
        return []

    spofs = []

    for node in graph.nodes():
        # Quanti componenti dipendono da questo (direttamente o indirettamente)
        try:
            dependents = list(nx.ancestors(graph, node))
        except nx.NetworkXError:
            dependents = []

        if len(dependents) > 0:
            node_data = graph.nodes[node]
            spofs.append({
                'part_number': node,
                'supplier': node_data.get('supplier', 'N/A'),
                'category': node_data.get('category', 'N/A'),
                'num_dependents': len(dependents),
                'dependent_pns': dependents,
                'impact': f"Blocca {len(dependents)} componenti: {', '.join(dependents)}",
            })

    # Ordina per impatto
    spofs.sort(key=lambda x: x['num_dependents'], reverse=True)
    return spofs


# =============================================================================
# VISUALIZZAZIONE MERMAID
# =============================================================================

def _mermaid_safe_id(text: str) -> str:
    """Genera un ID sicuro per nodi Mermaid (solo alfanumerici e underscore)."""
    import re
    return re.sub(r'[^a-zA-Z0-9_]', '_', str(text))


def _mermaid_sanitize(text: str) -> str:
    """Rimuove caratteri problematici per Mermaid: virgolette, pipe, parentesi, emoji."""
    import re
    # Rimuovi emoji e caratteri non-ASCII
    text = text.encode('ascii', 'ignore').decode('ascii')
    # Rimuovi caratteri che rompono la sintassi Mermaid
    text = text.replace('"', '').replace("'", '')
    text = text.replace('|', ' ').replace(',', ' -')
    text = text.replace('(', '').replace(')', '')
    text = text.replace('[', '').replace(']', '')
    text = text.replace('{', '').replace('}', '')
    text = text.replace('#', '').replace(';', ' ')
    text = text.replace('<', '').replace('>', '')
    # Collassa spazi multipli
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def render_dependency_tree(
    graph: Any,
    component_risks: Optional[Dict[str, Dict[str, Any]]] = None
) -> str:
    """
    Genera un diagramma Mermaid del grafo di dipendenze.

    Args:
        graph: networkx.DiGraph
        component_risks: Opzionale, per colorare i nodi

    Returns:
        Stringa con codice Mermaid
    """
    if graph is None or not HAS_NETWORKX:
        return "graph TD\n    NO[networkx non installato]"

    if len(graph.nodes()) == 0:
        return "graph TD\n    EMPTY[Nessuna dipendenza trovata]"

    lines = ["graph TD"]

    # Definisci nodi
    for node in graph.nodes():
        data = graph.nodes[node]
        supplier = str(data.get('supplier', ''))
        category = str(data.get('category', ''))
        standalone = data.get('standalone', True)

        # ID sicuro per Mermaid (rimuovi caratteri speciali)
        safe_id = _mermaid_safe_id(node)

        # Label: solo testo ASCII semplice, senza caratteri speciali Mermaid
        label_parts = [node]
        if supplier:
            label_parts.append(supplier)
        if category:
            label_parts.append(category)
        if not standalone:
            label_parts.append("non standalone")

        label = _mermaid_sanitize(" - ".join(label_parts))
        lines.append(f'    {safe_id}["{label}"]')

    # Definisci archi
    for source, target, data in graph.edges(data=True):
        safe_source = _mermaid_safe_id(source)
        safe_target = _mermaid_safe_id(target)
        dep_text = str(data.get('dependency_text', 'dipende da'))

        # Tronca testo lungo
        if len(dep_text) > 30:
            dep_text = dep_text[:27] + '...'

        # Sanitizza: rimuovi virgole, virgolette e caratteri speciali
        dep_text = _mermaid_sanitize(dep_text)

        lines.append(f'    {safe_source} -->|{dep_text}| {safe_target}')

    # Colora nodi per rischio
    if component_risks:
        red_nodes = []
        yellow_nodes = []
        green_nodes = []

        for node in graph.nodes():
            safe_id = _mermaid_safe_id(node)
            risk = component_risks.get(node, {})
            color = risk.get('color', 'GREEN')

            if color == 'RED':
                red_nodes.append(safe_id)
            elif color == 'YELLOW':
                yellow_nodes.append(safe_id)
            else:
                green_nodes.append(safe_id)

        lines.append("")
        lines.append("    classDef red fill:#ff4444,stroke:#c92a2a,color:#fff")
        lines.append("    classDef yellow fill:#ffbb33,stroke:#e67700,color:#000")
        lines.append("    classDef green fill:#00C851,stroke:#2f9e44,color:#fff")

        if red_nodes:
            lines.append(f"    class {','.join(red_nodes)} red")
        if yellow_nodes:
            lines.append(f"    class {','.join(yellow_nodes)} yellow")
        if green_nodes:
            lines.append(f"    class {','.join(green_nodes)} green")

    return "\n".join(lines)
