"""
Multi-Criteria Recovery Priority Index (MCPI) Pure Mathematical Service.

Phase 6D-B Milestone 1 Domain Implementation (Final Acceptance Audit).
Calculates multidimensional priority scores for post-disaster infrastructure
restoration projects using approved Phase 6D-A mathematical formulas:
- Configurable administrative policy weights (default: 0.30, 0.25, 0.20, 0.15, 0.10).
- Authoritative Stage 1 non-compensatory life-safety filter (TIER_1_MANDATORY).
- Numerical tier thresholds (>=70, >=50, >=30) marked strictly as INACTIVE optional policy proposals.
- Deterministic stable tie-breaking: substantive criteria (MCPI -> phi_L -> phi_V -> cascade -> cost)
  followed strictly by ascending project_id as a non-substantive final arbiter.
- Confidence decay and data freshness do NOT reduce project priority.

Pure mathematical logic: independent of database persistence and API routes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class MCPIWeights:
    """
    Configurable administrative policy criteria weights.
    These weights represent administrative policy assumptions, NOT statutory mandates.
    Sum must equal 1.0 within numerical tolerance.
    """
    life_safety: float = 0.30             # w_L: Life safety policy weight
    criticality: float = 0.25             # w_C: Infrastructure criticality policy weight
    vulnerability: float = 0.20           # w_V: Demographic vulnerability policy weight
    dependency: float = 0.15              # w_D: Dependency importance policy weight
    economic: float = 0.10                # w_E: Economic impact policy weight

    def __post_init__(self):
        for name, w in [
            ("life_safety", self.life_safety),
            ("criticality", self.criticality),
            ("vulnerability", self.vulnerability),
            ("dependency", self.dependency),
            ("economic", self.economic),
        ]:
            if w < 0.0 or w > 1.0:
                raise ValueError(f"Weight '{name}' must be between 0.0 and 1.0, got {w}")
        
        total = sum([self.life_safety, self.criticality, self.vulnerability, self.dependency, self.economic])
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Policy criteria weights must sum to 1.0, got {total:.6f}")


@dataclass(frozen=True)
class MCPITierThresholds:
    """
    INACTIVE Optional Policy Proposal: Arbitrary numerical tier thresholds (>=70, >=50, >=30).
    Marked strictly as an inactive, optional administrative policy proposal requiring
    explicit project-owner authorization before activation.
    """
    is_active: bool = False               # Inactive by default; unapproved policy addition
    tier1_threshold: float = 70.0
    tier2_threshold: float = 50.0
    tier3_threshold: float = 30.0

    def __post_init__(self):
        if not (self.tier1_threshold > self.tier2_threshold > self.tier3_threshold >= 0.0):
            raise ValueError("Tier thresholds must strictly descend: tier1 > tier2 > tier3 >= 0.0")


@dataclass
class MCPIInput:
    """
    Project-specific attribute inputs for MCPI evaluation.
    All normalized criteria scores (phi_k) must lie in [0.0, 1.0].
    """
    project_id: str
    project_code: str
    phi_life_safety: float      # phi_L in [0.0, 1.0]
    phi_criticality: float      # phi_C in [0.0, 1.0]
    phi_vulnerability: float    # phi_V in [0.0, 1.0]
    phi_dependency: float       # phi_D in [0.0, 1.0]
    phi_economic: float         # phi_E in [0.0, 1.0]
    estimated_cost: float       # Capital cost in currency units (used for tie-breaking)
    transitive_cascade: int = 0 # Downstream reachable vertices in DAG (tie-breaking)
    is_tier1_mandatory: bool = False # Elevates to TIER_1_MANDATORY without compensatory trade-offs


@dataclass
class MCPIResult:
    """
    Computed priority evaluation result with audit metadata.
    """
    project_id: str
    project_code: str
    raw_score: float             # In [0.0, 1.0]
    mcpi_score: float            # Scaled to [0.0, 100.0]
    priority_designation: str    # Authoritative designation: TIER_1_MANDATORY or STANDARD_RECOVERY
    component_contributions: Dict[str, float]
    is_tier1_mandatory: bool
    policy_disclosure: str       # Documentation of administrative policy status
    experimental_policy_tier: Optional[str] = None # Inactive optional proposal (only populated if explicitly activated)


class MCPIPrioritizationService:
    """
    Pure mathematical engine for Multi-Criteria Recovery Prioritization.
    """
    POLICY_DISCLOSURE: str = (
        "MCPI criteria weights are configurable administrative policy assumptions established "
        "under Phase 6D-A, not statutory mandates. The only authoritative priority tier is "
        "TIER_1_MANDATORY for critical life-safety breaches (S_L >= 0.85). Numerical score tiers "
        "(>=70, >=50, >=30) are inactive optional proposals requiring project-owner approval. "
        "Confidence decay and data freshness do not reduce project priority."
    )

    @staticmethod
    def validate_input(item: MCPIInput) -> None:
        """Validates that all input criteria lie strictly in [0.0, 1.0]."""
        for attr, val in [
            ("phi_life_safety", item.phi_life_safety),
            ("phi_criticality", item.phi_criticality),
            ("phi_vulnerability", item.phi_vulnerability),
            ("phi_dependency", item.phi_dependency),
            ("phi_economic", item.phi_economic),
        ]:
            if val < 0.0 or val > 1.0:
                raise ValueError(f"Criterion '{attr}' must be in [0.0, 1.0], got {val}")
        if item.estimated_cost < 0.0:
            raise ValueError(f"Estimated cost cannot be negative, got {item.estimated_cost}")

    @classmethod
    def calculate_single(
        cls,
        item: MCPIInput,
        weights: Optional[MCPIWeights] = None,
        tier_proposals: Optional[MCPITierThresholds] = None,
    ) -> MCPIResult:
        """
        Calculates the MCPI composite score for a single project:
        MCPI = 100 * (w_L*phi_L + w_C*phi_C + w_V*phi_V + w_D*phi_D + w_E*phi_E)
        
        Active Authoritative Designation:
        - TIER_1_MANDATORY if item.is_tier1_mandatory is True
        - STANDARD_RECOVERY otherwise.
        
        Arbitrary numerical tiers (>=70, >=50, >=30) are strictly inactive by default.
        """
        cls.validate_input(item)
        if weights is None:
            weights = MCPIWeights()
        if tier_proposals is None:
            tier_proposals = MCPITierThresholds()

        contributions = {
            "life_safety": weights.life_safety * item.phi_life_safety,
            "criticality": weights.criticality * item.phi_criticality,
            "vulnerability": weights.vulnerability * item.phi_vulnerability,
            "dependency": weights.dependency * item.phi_dependency,
            "economic": weights.economic * item.phi_economic,
        }

        raw_score = sum(contributions.values())
        mcpi_score = round(raw_score * 100.0, 4)

        # Authoritative designation
        if item.is_tier1_mandatory:
            designation = "TIER_1_MANDATORY"
        else:
            designation = "STANDARD_RECOVERY"

        # Inactive optional proposal (only populated if explicitly active)
        experimental_tier = None
        if tier_proposals.is_active:
            if item.is_tier1_mandatory:
                experimental_tier = "PROPOSAL_TIER_1"
            elif mcpi_score >= tier_proposals.tier1_threshold:
                experimental_tier = "PROPOSAL_TIER_1"
            elif mcpi_score >= tier_proposals.tier2_threshold:
                experimental_tier = "PROPOSAL_TIER_2"
            elif mcpi_score >= tier_proposals.tier3_threshold:
                experimental_tier = "PROPOSAL_TIER_3"
            else:
                experimental_tier = "PROPOSAL_TIER_4"

        return MCPIResult(
            project_id=item.project_id,
            project_code=item.project_code,
            raw_score=round(raw_score, 6),
            mcpi_score=mcpi_score,
            priority_designation=designation,
            component_contributions=contributions,
            is_tier1_mandatory=item.is_tier1_mandatory,
            policy_disclosure=cls.POLICY_DISCLOSURE,
            experimental_policy_tier=experimental_tier,
        )

    @classmethod
    def rank_portfolio(
        cls,
        items: List[MCPIInput],
        weights: Optional[MCPIWeights] = None,
    ) -> List[MCPIResult]:
        """
        Evaluates and deterministically sorts a portfolio of projects using
        ONLY criteria explicitly authorized in Phase 6D-A:
        1. Stage 1 Non-Compensatory Filter: Tier 1 Mandatory projects first (is_tier1_mandatory).
        2. Primary Substantive Criterion: Exact unrounded MCPI raw score (descending).
        3. First Substantive Tie-Breaker: phi_life_safety (descending, exact float).
        4. Second Substantive Tie-Breaker: phi_vulnerability (descending, exact float).
        5. Third Substantive Tie-Breaker: transitive_cascade (descending, exact integer).
        6. Fourth Substantive Tie-Breaker: estimated_cost (ascending, exact float, cost-effectiveness).
        7. Stable Non-Substantive Final Arbiter: project_id (ascending alphabetical).

        Mathematical Exactness Invariant:
        Tolerance-based substantive grouping is strictly disallowed. Project ID acts
        as an arbiter ONLY when all six substantive criteria above are mathematically
        equal. A real substantive difference (even < 1e-4) strictly takes precedence
        over project ID.
        """
        results = [cls.calculate_single(item, weights) for item in items]
        input_map = {item.project_id: item for item in items}

        def substantive_sort_key(res: MCPIResult):
            inp = input_map[res.project_id]
            return (
                1 if res.is_tier1_mandatory else 0, # Stage 1 non-compensatory filter
                res.raw_score,                      # Exact unrounded MCPI score (prevents 1e-4 rounding overrides)
                inp.phi_life_safety,                # Tie-breaker 1 (exact float)
                inp.phi_vulnerability,              # Tie-breaker 2 (exact float)
                inp.transitive_cascade,             # Tie-breaker 3 (exact integer)
                -inp.estimated_cost,                # Tie-breaker 4 (exact float, lower cost first)
            )

        # Python's list.sort() is Timsort, which is guaranteed stable.
        # Step 1: Pre-sort ascending by project_id (non-substantive stable fallback)
        results.sort(key=lambda r: r.project_id)
        # Step 2: Stable sort descending by authorized substantive hierarchy (exact comparison)
        results.sort(key=substantive_sort_key, reverse=True)
        return results
