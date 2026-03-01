"""
alert_engine.py — KRI Threshold Alert Engine (v4.3)
=====================================================
Controlla i componenti analizzati rispetto alle soglie KRI (Key Risk Indicator)
e genera alert strutturati per la Dashboard.

Tipi di alert:
    CRITICAL      — componente supera soglia RED
    NEW_HIGH      — componente nuovo/peggiorato rispetto allo snapshot precedente
    SCORE_INCREASE — score aumentato > SCORE_DELTA_THRESHOLD rispetto allo snapshot
"""

from datetime import datetime
from typing import Dict, List, Optional

# Soglia di incremento score per triggerare alert SCORE_INCREASE
SCORE_DELTA_THRESHOLD = 10


def check_kri_alerts(
    batch_results: dict,
    risk_appetite: Optional[Dict[str, int]] = None,
    previous_snapshot: Optional[dict] = None,
) -> List[Dict]:
    """
    Controlla i componenti analizzati e genera lista di alert KRI.

    Args:
        batch_results:      Output di _run_batch_analysis() con chiave 'components_risk'
        risk_appetite:      {'high': int, 'medium': int} — soglie per il cliente
                            Se None usa i default (HIGH=55, MEDIUM=30)
        previous_snapshot:  Snapshot precedente (batch_results di analisi precedente)
                            Usato per rilevare peggioramenti. Se None solo alert assoluti.

    Returns:
        Lista di dict con chiavi:
            severity    — 'CRITICAL' | 'HIGH' | 'WARNING'
            alert_type  — 'threshold_breach' | 'new_high' | 'score_increase'
            part_number — str
            supplier    — str
            score       — float
            message     — str (testo leggibile)
            timestamp   — str ISO
    """
    appetite = risk_appetite or {'high': 55, 'medium': 30}
    high_thresh = appetite.get('high', 55)

    components = batch_results.get('components_risk', [])
    alerts: List[Dict] = []
    ts = datetime.now().isoformat()

    # Mappa snapshot precedente per lookup rapido
    prev_map: Dict[str, float] = {}
    if previous_snapshot:
        for r in previous_snapshot.get('components_risk', []):
            pn = str(r.get('part_number', '')).upper()
            prev_map[pn] = float(r.get('score', 0))

    for comp in components:
        pn = str(comp.get('part_number', '')).upper()
        score = float(comp.get('score', 0))
        supplier = str(comp.get('supplier', ''))
        risk_level = str(comp.get('risk_level', ''))

        # --- Alert 1: threshold breach (CRITICAL) ---
        if risk_level == 'HIGH' or score >= high_thresh:
            alerts.append({
                'severity': 'CRITICAL',
                'alert_type': 'threshold_breach',
                'part_number': pn,
                'supplier': supplier,
                'score': score,
                'message': (
                    f"{pn} ({supplier}) supera la soglia HIGH con score {score:.0f} "
                    f"(soglia: {high_thresh}). Azione immediata richiesta."
                ),
                'timestamp': ts,
            })
            continue  # non aggiungere alert duplicati per lo stesso PN

        # --- Alert 2: NEW_HIGH (componente passato da non-HIGH a HIGH) ---
        if pn in prev_map:
            prev_score = prev_map[pn]
            delta = score - prev_score

            if prev_score < high_thresh and score >= high_thresh:
                alerts.append({
                    'severity': 'HIGH',
                    'alert_type': 'new_high',
                    'part_number': pn,
                    'supplier': supplier,
                    'score': score,
                    'message': (
                        f"{pn} e' passato a livello HIGH (da {prev_score:.0f} a {score:.0f}, "
                        f"delta +{delta:.0f}). Verificare causa."
                    ),
                    'timestamp': ts,
                })

            # --- Alert 3: SCORE_INCREASE (peggioramento significativo) ---
            elif delta >= SCORE_DELTA_THRESHOLD:
                alerts.append({
                    'severity': 'WARNING',
                    'alert_type': 'score_increase',
                    'part_number': pn,
                    'supplier': supplier,
                    'score': score,
                    'message': (
                        f"{pn} ha aumentato il risk score di +{delta:.0f} punti "
                        f"({prev_score:.0f} → {score:.0f}). Monitorare la situazione."
                    ),
                    'timestamp': ts,
                })

    # Ordina per severity: CRITICAL > HIGH > WARNING
    _sev_order = {'CRITICAL': 0, 'HIGH': 1, 'WARNING': 2}
    alerts.sort(key=lambda a: _sev_order.get(a['severity'], 9))
    return alerts


def get_alert_summary(alerts: List[Dict]) -> Dict[str, int]:
    """
    Ritorna conteggio alert per severity.

    Returns:
        {'CRITICAL': n, 'HIGH': n, 'WARNING': n, 'total': n}
    """
    summary = {'CRITICAL': 0, 'HIGH': 0, 'WARNING': 0}
    for a in alerts:
        sev = a.get('severity', 'WARNING')
        if sev in summary:
            summary[sev] += 1
    summary['total'] = sum(summary.values())
    return summary
