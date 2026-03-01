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

# v4.3 - Importa costanti e tipi centralizzati
from grc_constants import (
    DEFAULT_RISK_APPETITE,
    SCORE_DELTA_THRESHOLD,
    MAX_CRITICAL_ALERTS_DISPLAY,
    AlertSeverity,
    AlertType,
)


def check_kri_alerts(
    batch_results: dict,
    risk_appetite: Optional[Dict[str, int]] = None,
    previous_snapshot: Optional[dict] = None,
) -> List[Dict]:
    """
    Controlla i componenti analizzati e genera lista di alert KRI.

    Ottimizzato con early termination: se troppi CRITICAL, interrompe l'elaborazione
    per evitare overloading.

    Args:
        batch_results:      Output di _run_batch_analysis() con chiave 'components_risk'
        risk_appetite:      {'high': int, 'medium': int} — soglie per il cliente
                            Se None usa i default (HIGH=55, MEDIUM=30)
        previous_snapshot:  Snapshot precedente (batch_results di analisi precedente)
                            Usato per rilevare peggioramenti. Se None solo alert assoluti.

    Returns:
        Lista di dict con chiavi:
            severity    — AlertSeverity enum (CRITICAL/HIGH/WARNING)
            alert_type  — AlertType enum (threshold_breach/new_high/score_increase)
            part_number — str
            supplier    — str
            score       — float
            message     — str (testo leggibile)
            timestamp   — str ISO
    """
    appetite = risk_appetite or DEFAULT_RISK_APPETITE
    high_thresh = appetite.get('high', 55)

    components = batch_results.get('components_risk', [])
    alerts: List[Dict] = []
    ts = datetime.now().isoformat()

    # Mappa snapshot precedente per lookup rapido (lazy load)
    prev_map: Dict[str, float] = {}
    if previous_snapshot:
        prev_map = {
            str(r.get('part_number', '')).upper(): float(r.get('score', 0))
            for r in previous_snapshot.get('components_risk', [])
        }

    critical_count = 0

    for comp in components:
        pn = str(comp.get('part_number', '')).upper()
        score = float(comp.get('score', 0))
        supplier = str(comp.get('supplier', ''))
        risk_level = str(comp.get('risk_level', ''))

        # --- Alert 1: threshold breach (CRITICAL) ---
        if risk_level == 'HIGH' or score >= high_thresh:
            alerts.append({
                'severity': AlertSeverity.CRITICAL.value,
                'alert_type': AlertType.THRESHOLD_BREACH.value,
                'part_number': pn,
                'supplier': supplier,
                'score': score,
                'message': (
                    f"{pn} ({supplier}) supera la soglia HIGH con score {score:.0f} "
                    f"(soglia: {high_thresh}). Azione immediata richiesta."
                ),
                'timestamp': ts,
            })
            critical_count += 1

            # Early termination: se troppi CRITICAL, skip altri check per questo PN
            if critical_count >= MAX_CRITICAL_ALERTS_DISPLAY:
                continue
            else:
                continue  # Skip altri alert per questo componente

        # --- Alert 2: NEW_HIGH (componente passato da non-HIGH a HIGH) ---
        if pn in prev_map:
            prev_score = prev_map[pn]
            delta = score - prev_score

            if prev_score < high_thresh and score >= high_thresh:
                alerts.append({
                    'severity': AlertSeverity.HIGH.value,
                    'alert_type': AlertType.NEW_HIGH.value,
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
                    'severity': AlertSeverity.WARNING.value,
                    'alert_type': AlertType.SCORE_INCREASE.value,
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
    alerts.sort(key=lambda a: AlertSeverity(a['severity']).order)

    return alerts


def get_alert_summary(alerts: List[Dict]) -> Dict[str, int]:
    """
    Ritorna conteggio alert per severity.

    Args:
        alerts: Lista di alert da check_kri_alerts()

    Returns:
        {'CRITICAL': n, 'HIGH': n, 'WARNING': n, 'total': n}
    """
    summary = {
        AlertSeverity.CRITICAL.value: 0,
        AlertSeverity.HIGH.value: 0,
        AlertSeverity.WARNING.value: 0,
    }
    for a in alerts:
        sev = a.get('severity', AlertSeverity.WARNING.value)
        if sev in summary:
            summary[sev] += 1

    summary['total'] = sum(summary.values())
    return summary
