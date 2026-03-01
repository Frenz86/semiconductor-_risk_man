"""
grc_constants.py — Costanti e Enum per feature GRC v4.3
======================================================
Centralizza magic numbers, tipi e costanti per risk appetite, alert severity,
e action types - evita duplicazioni e stringly-typed code.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict


# =============================================================================
# COSTANTI RISK APPETITE (soglie default)
# =============================================================================
DEFAULT_RISK_APPETITE_HIGH = 55
DEFAULT_RISK_APPETITE_MEDIUM = 30
DEFAULT_RISK_APPETITE: Dict[str, int] = {'high': DEFAULT_RISK_APPETITE_HIGH, 'medium': DEFAULT_RISK_APPETITE_MEDIUM}

# BOM Value thresholds per P×I Impact calculation
BOM_VALUE_THRESHOLDS = {
    'very_high': 500,   # >$500 → Impact 5
    'high': 200,        # >$200 → Impact 4
    'medium': 50,       # >$50 → Impact 3
    'low': 10,          # >$10 → Impact 2
    'minimal': 0,       # ≤$10 → Impact 1
}

# P×I Score thresholds
PX_SCORE_RED_THRESHOLD = 12      # >= 12 → RED
PX_SCORE_YELLOW_THRESHOLD = 6    # >= 6 → YELLOW
PX_SCORE_MAX = 25                # 5×5 max score

# Alert thresholds
SCORE_DELTA_THRESHOLD = 10        # +10pt → SCORE_INCREASE alert
MAX_CRITICAL_ALERTS_DISPLAY = 10  # Max CRITICAL alerts before early termination


# =============================================================================
# ENUMS
# =============================================================================

class AlertSeverity(str, Enum):
    """Livelli di severita per gli alert KRI"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    WARNING = "WARNING"

    @property
    def order(self) -> int:
        """Ordinamento: CRITICAL (0) > HIGH (1) > WARNING (2)"""
        return {AlertSeverity.CRITICAL: 0, AlertSeverity.HIGH: 1, AlertSeverity.WARNING: 2}[self]

    @property
    def emoji(self) -> str:
        """Icona emoji per visualizzazione"""
        return {
            AlertSeverity.CRITICAL: "🔴",
            AlertSeverity.HIGH: "🟠",
            AlertSeverity.WARNING: "🟡",
        }[self]


class AlertType(str, Enum):
    """Tipi di alert KRI"""
    THRESHOLD_BREACH = "threshold_breach"
    NEW_HIGH = "new_high"
    SCORE_INCREASE = "score_increase"


class RiskStatus(str, Enum):
    """Stato del rischio per Risk Ownership"""
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    ACCEPTED = "Accepted"
    MITIGATED = "Mitigated"


class ActionType(str, Enum):
    """Tipi di azione per Activity Log"""
    RISK_ANALYSIS = "risk_analysis"
    OWNER_ASSIGNED = "owner_assigned"
    RISK_ACCEPTED = "risk_accepted"
    MITIGATION_STARTED = "mitigation_started"
    MITIGATION_COMPLETED = "mitigation_completed"
    THRESHOLD_CHANGED = "threshold_changed"
    SNAPSHOT_SAVED = "snapshot_saved"


class RiskLevel(str, Enum):
    """Livelli di rischio standard"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def from_score(cls, score: float, high_thresh: int, medium_thresh: int) -> 'RiskLevel':
        """Deriva RiskLevel dal score e dalle soglie"""
        if score >= high_thresh:
            return cls.HIGH
        elif score >= medium_thresh:
            return cls.MEDIUM
        return cls.LOW


# =============================================================================
# DATA CLASS per parametri complessi
# =============================================================================

@dataclass
class RiskAppetite:
    """Soglie di rischio configurabili per cliente"""
    high: int = DEFAULT_RISK_APPETITE_HIGH
    medium: int = DEFAULT_RISK_APPETITE_MEDIUM

    def to_dict(self) -> Dict[str, int]:
        return {'high': self.high, 'medium': self.medium}

    @classmethod
    def from_dict(cls, d: Dict[str, int]) -> 'RiskAppetite':
        return cls(high=d.get('high', DEFAULT_RISK_APPETITE_HIGH),
                   medium=d.get('medium', DEFAULT_RISK_APPETITE_MEDIUM))

    def validate(self) -> bool:
        """Verifica che high > medium"""
        return self.high > self.medium


@dataclass
class ActivityLogEntry:
    """Entry per Activity Log - tipato e validato"""
    client_id: str
    action_type: ActionType
    target_pn: str = ""
    old_value: str = ""
    new_value: str = ""
    notes: str = ""
    user: str = "system"

    def to_dict(self) -> Dict[str, str]:
        """Converte in dict per salvataggio Excel"""
        return {
            'Client_ID': self.client_id,
            'Action_Type': self.action_type.value,
            'Target_PN': self.target_pn,
            'Old_Value': self.old_value,
            'New_Value': self.new_value,
            'Notes': self.notes,
            'User': self.user,
        }

    @classmethod
    def create_owner_change(cls, client_id: str, pn: str, old_data: dict, new_data: dict, user: str = "system") -> 'ActivityLogEntry':
        """Factory per azione owner_assigned"""
        return cls(
            client_id=client_id,
            action_type=ActionType.OWNER_ASSIGNED,
            target_pn=pn,
            old_value=f"owner={old_data.get('owner', '')}, status={old_data.get('status', '')}",
            new_value=f"owner={new_data.get('owner', '')}, status={new_data.get('status', '')}",
            notes=f"Risk owner changed for {pn}",
            user=user,
        )

    @classmethod
    def create_threshold_change(cls, client_id: str, old_appetite: dict, new_appetite: dict, user: str = "system") -> 'ActivityLogEntry':
        """Factory per azione threshold_changed"""
        return cls(
            client_id=client_id,
            action_type=ActionType.THRESHOLD_CHANGED,
            old_value=f"HIGH={old_appetite.get('high')}, MEDIUM={old_appetite.get('medium')}",
            new_value=f"HIGH={new_appetite.get('high')}, MEDIUM={new_appetite.get('medium')}",
            notes="Risk Appetite thresholds updated",
            user=user,
        )

    @classmethod
    def create_risk_analysis(cls, client_id: str, bom_name: str, high_count: int, total_count: int, user: str = "system") -> 'ActivityLogEntry':
        """Factory per azione risk_analysis"""
        return cls(
            client_id=client_id,
            action_type=ActionType.RISK_ANALYSIS,
            new_value=f"BOM={bom_name}, HIGH={high_count}",
            notes=f"Batch analysis {total_count} components",
            user=user,
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def validate_risk_appetite_value(value, default: int) -> int:
    """
    Valida e converte un valore di risk appetite.

    Args:
        value: Valore da validare (può essere None, stringa, numero)
        default: Valore default se validation fallisce

    Returns:
        int: Valore validato
    """
    if value is None or str(value).strip() in ('', 'nan', 'None'):
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def format_owner_change(old_data: dict, new_data: dict) -> tuple[str, str]:
    """
    Formatta i dati per il log di cambio owner.

    Returns:
        (old_value, new_value) tuple
    """
    old_str = f"owner={old_data.get('owner', '')}, status={old_data.get('status', 'Open')}"
    new_str = f"owner={new_data.get('owner', '')}, status={new_data.get('status', 'Open')}"
    return old_str, new_str
