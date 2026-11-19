"""
Life-Safety Triage Pure Mathematical Service.

Phase 6D-B Milestone 1 Domain Implementation.
Calculates composite life-safety risk scores (S_L) and evaluates non-compensatory
Tier 1 fast-tracking triggers using approved Phase 6D-A mathematical formulas:
- Convex combination of structural damage, secondary environmental hazard, and occupancy exposure.
- Strict bounded evaluation in [0.0, 1.0].
- Administrative policy threshold evaluation (tau_L = 0.85).

Pure mathematical logic: independent of database persistence and API routes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Union


class StructuralDamageSeverity(str, Enum):
    """Discrete structural damage severity rating."""
    NONE = "NONE"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    COLLAPSED = "COLLAPSED"
    DESTROYED = "DESTROYED"


DAMAGE_RATING_MAP: Dict[StructuralDamageSeverity, float] = {
    StructuralDamageSeverity.NONE: 0.0,
    StructuralDamageSeverity.MINOR: 0.25,
    StructuralDamageSeverity.MODERATE: 0.50,
    StructuralDamageSeverity.SEVERE: 0.75,
    StructuralDamageSeverity.COLLAPSED: 1.00,
    StructuralDamageSeverity.DESTROYED: 1.00,
}


@dataclass(frozen=True)
class LifeSafetyWeights:
    """
    Normalized life-safety component weights.
    w_damage (0.70) + w_secondary (0.20) + w_occupancy (0.10) == 1.0.
    """
    damage: float = 0.70
    secondary_hazard: float = 0.20
    occupancy: float = 0.10

    def __post_init__(self):
        for name, w in [
            ("damage", self.damage),
            ("secondary_hazard", self.secondary_hazard),
            ("occupancy", self.occupancy),
        ]:
            if w < 0.0 or w > 1.0:
                raise ValueError(f"Weight '{name}' must be in [0.0, 1.0], got {w}")
        
        total = self.damage + self.secondary_hazard + self.occupancy
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Life safety weights must sum to 1.0, got {total:.6f}")


@dataclass
class LifeSafetyInput:
    """
    Inputs for life-safety triage evaluation.
    phi_damage can be passed as continuous float in [0.0, 1.0] or as StructuralDamageSeverity enum/string.
    """
    damage_score: Union[float, StructuralDamageSeverity, str]
    secondary_hazard_score: float   # H_secondary in [0.0, 1.0] (landslide/flood/electrical hazard)
    occupancy_score: float          # Omega_occupancy in [0.0, 1.0] (human density/exposure factor)


@dataclass
class LifeSafetyResult:
    """
    Computed life-safety triage result with non-compensatory Tier 1 flag.
    """
    score_life_safety: float         # S_L in [0.0, 1.0]
    is_tier1_mandatory: bool         # S_L >= tau_L (0.85) triggers non-compensatory fast-tracking
    triage_threshold: float          # tau_L (default 0.85)
    normalized_damage: float         # phi_damage in [0.0, 1.0]
    secondary_hazard: float          # H_secondary in [0.0, 1.0]
    occupancy_exposure: float        # Omega_occupancy in [0.0, 1.0]
    component_contributions: Dict[str, float]
    policy_disclosure: str           # Explicit statement of administrative triage semantics


class LifeSafetyTriageService:
    """
    Pure mathematical service for life-safety triage and Tier 1 elevation.
    """
    DEFAULT_TRIAGE_THRESHOLD_TAU_L: float = 0.85
    POLICY_DISCLOSURE_TEXT: str = (
        "tau_L = 0.85 is an administrative policy triage parameter established under "
        "Phase 6D-A for rapid disaster recovery fast-tracking. It is NOT an empirical civil "
        "engineering structural collapse probability or limit-state reliability index, does NOT "
        "constitute structural engineering certification, and does NOT treat administrative GOVT "
        "verification as a substitute for professional engineering licensure."
    )

    @classmethod
    def resolve_damage_score(cls, damage_input: Union[float, StructuralDamageSeverity, str]) -> float:
        """Converts damage input (enum, string, or float) to bounded float in [0.0, 1.0]."""
        if isinstance(damage_input, (int, float)):
            val = float(damage_input)
            if val < 0.0 or val > 1.0:
                raise ValueError(f"Damage score float must be in [0.0, 1.0], got {val}")
            return val
        
        # Handle string or Enum
        if isinstance(damage_input, str):
            clean_str = damage_input.strip().upper()
            try:
                severity = StructuralDamageSeverity(clean_str)
                return DAMAGE_RATING_MAP[severity]
            except ValueError:
                # Attempt float parse
                try:
                    val = float(clean_str)
                    if 0.0 <= val <= 1.0:
                        return val
                except ValueError:
                    pass
                raise ValueError(f"Unknown damage severity rating: '{damage_input}'")
        
        if isinstance(damage_input, StructuralDamageSeverity):
            return DAMAGE_RATING_MAP[damage_input]

        raise TypeError(f"Unsupported damage_score type: {type(damage_input)}")

    @classmethod
    def evaluate(
        cls,
        inp: LifeSafetyInput,
        weights: Optional[LifeSafetyWeights] = None,
        tau_l: Optional[float] = None,
    ) -> LifeSafetyResult:
        """
        Calculates S_L = w_damage * phi_damage + w_sec * H_sec + w_occ * Omega_occ.
        Evaluates non-compensatory Tier 1 trigger against tau_L.
        """
        if weights is None:
            weights = LifeSafetyWeights()
        if tau_l is None:
            tau_l = cls.DEFAULT_TRIAGE_THRESHOLD_TAU_L

        if tau_l <= 0.0 or tau_l > 1.0:
            raise ValueError(f"Triage threshold tau_L must be in (0.0, 1.0], got {tau_l}")

        phi_damage = cls.resolve_damage_score(inp.damage_score)

        if inp.secondary_hazard_score < 0.0 or inp.secondary_hazard_score > 1.0:
            raise ValueError(f"Secondary hazard score must be in [0.0, 1.0], got {inp.secondary_hazard_score}")
        if inp.occupancy_score < 0.0 or inp.occupancy_score > 1.0:
            raise ValueError(f"Occupancy score must be in [0.0, 1.0], got {inp.occupancy_score}")

        c_damage = weights.damage * phi_damage
        c_secondary = weights.secondary_hazard * inp.secondary_hazard_score
        c_occupancy = weights.occupancy * inp.occupancy_score

        s_l = c_damage + c_secondary + c_occupancy
        s_l_clamped = min(1.0, max(0.0, s_l))

        is_mandatory = s_l_clamped >= (tau_l - 1e-9)

        return LifeSafetyResult(
            score_life_safety=round(s_l_clamped, 6),
            is_tier1_mandatory=is_mandatory,
            triage_threshold=tau_l,
            normalized_damage=round(phi_damage, 4),
            secondary_hazard=round(inp.secondary_hazard_score, 4),
            occupancy_exposure=round(inp.occupancy_score, 4),
            component_contributions={
                "damage": round(c_damage, 6),
                "secondary_hazard": round(c_secondary, 6),
                "occupancy": round(c_occupancy, 6),
            },
            policy_disclosure=cls.POLICY_DISCLOSURE_TEXT,
        )
