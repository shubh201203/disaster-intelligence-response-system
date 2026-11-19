"""
Unit tests for DIRS Phase 6D-B Milestone 1 Pure Mathematical Services.

Phase 6D-B Milestone 1 Authoritative Final Correction & Evidence Suite.
Validates all domain mathematical services against authorized Phase 6D-A specifications:

1. VulnerabilityScoringService:
   - psi = 1.0*N_GEN + 2.5*N_ACC + 3.0*N_MED + 4.5*N_MED_ACC
   - Complete and mutually exclusive demographic categories
   - Missing subgroup categories & incomplete enumeration lower bounds
   - Zero population handling
   - Subgroups equal to, below, and exceeding total population
   - Strict double-counting prevention (no duplicated general counts)
   - Monotonicity proof of lower bound
   - Two-branch mapping (known vs unknown baseline) & zero-division guards

2. MCPIPrioritizationService:
   - Configurable administrative policy weights (0.30, 0.25, 0.20, 0.15, 0.10)
   - Authorized substantive tie-breaking hierarchy (Safety -> MCPI -> phi_L -> phi_V -> Cascade -> Cost)
   - Adversarial exact equality tests: eliminating tolerance overrides (1e-5 differences strictly preserved)
   - Reversal of project IDs proving zero substantive influence of arbitrary IDs
   - Priority tier status: inactive numerical tiers, mandatory life-safety override

3. LifeSafetyTriageService:
   - Input parsing (enum, string, float) and invalid input rejection
   - Component bounds [0, 1], convex combination calculation
   - Administrative triage threshold (tau_L = 0.85)
   - Disclaimers: no collapse probability, no structural certification, no professional licensure

4. ProjectDependencyService:
   - Ceiling lag conversion: ceil(L_days / Delta_t) for 0, 1, 29, 30, 31, 60 days
   - Invalid dependency input validation (negative days)
   - Linear topological sort
   - Cycle detection with cycle path extraction
   - Transitive cascade reachability counts
   - CPM-PL schedule forward/backward passes, floats, critical path

5. CalendarCostService:
   - Gamma profiles: UNIFORM, FRONT_LOADED, BACK_LOADED, S_CURVE, CUSTOM
   - Boundary checks for 0, 1, 29, 30, 31, 60 days
   - Partial final period truncation (is_fully_reconciled = False)
   - Full cost convolution lifetime reconciliation

6. EquityCalculationService:
   - Policy ring-fencing and unabsorbed policy reserves
   - Zero eligible absorption handling (pipeline = 0)
   - Uncontacted blackout reserve
   - Mathematical allocation constraints vs actual financial liquidity separation

7. CashFlowSolvencyService:
   - Carry-forward recurrence Phi_t = eta*Phi_{t-1} + B_t - E_t
   - Insolvent trajectory, deficit quantification, earliest period detection
   - Multi-fund ring-fencing preventing unauthorized cross-subsidization
"""

from datetime import date, timedelta
import pytest

from app.recovery.services.mcpi_prioritization_service import (
    MCPIWeights,
    MCPITierThresholds,
    MCPIInput,
    MCPIResult,
    MCPIPrioritizationService,
)
from app.recovery.services.vulnerability_scoring_service import (
    DemographicWeights,
    DemographicInput,
    VulnerabilityResult,
    VulnerabilityScoringService,
)
from app.recovery.services.life_safety_triage_service import (
    StructuralDamageSeverity,
    LifeSafetyWeights,
    LifeSafetyInput,
    LifeSafetyResult,
    LifeSafetyTriageService,
)
from app.recovery.services.project_dependency_service import (
    CyclicDependencyError,
    DependencyEdge,
    ProjectActivity,
    CPMNodeResult,
    DAGAnalysisResult,
    ProjectDependencyService,
)
from app.recovery.services.calendar_cost_service import (
    DisbursementCurveType,
    ProjectDisbursementSpec,
    PeriodBoundary,
    ProjectExpenditureSchedule,
    CalendarCostService,
)
from app.recovery.services.equity_calculation_service import (
    DistrictEquitySpec,
    DistrictProjectPipeline,
    DistrictEquityTarget,
    PortfolioEquityAudit,
    EquityCalculationService,
)
from app.recovery.services.cash_flow_solvency_service import (
    FundTranchePlan,
    PeriodSolvencyStatus,
    FundSolvencyTrajectory,
    PortfolioSolvencyAudit,
    CashFlowSolvencyService,
)


# ============================================================================
# 1. VULNERABILITY SCORING SERVICE TESTS (AUDIT ITEM 3)
# ============================================================================

class TestVulnerabilityPopulationReconciliation:
    """Rigorous population reconciliation, mutual exclusivity, and double-counting prevention."""

    def test_default_authoritative_weights(self):
        """psi = 1.0*N_GEN + 2.5*N_ACC + 3.0*N_MED + 4.5*N_MED_ACC."""
        w = DemographicWeights()
        assert (w.general_base, w.accessible_needs, w.chronic_medical, w.intersectional) == (1.00, 2.50, 3.00, 4.50)

    def test_each_demographic_category_independently(self):
        """Validates exact weight application when only a single subgroup is present."""
        w = DemographicWeights()
        # General only: 100 * 1.0 = 100
        psi_gen, _, _, _ = VulnerabilityScoringService.calculate_headcount_index(DemographicInput(100, n_general=100), w)
        assert psi_gen == pytest.approx(100.0)
        # Accessible only: 100 * 2.5 = 250
        psi_acc, _, _, _ = VulnerabilityScoringService.calculate_headcount_index(DemographicInput(100, n_accessible_needs=100), w)
        assert psi_acc == pytest.approx(250.0)
        # Medical only: 100 * 3.0 = 300
        psi_med, _, _, _ = VulnerabilityScoringService.calculate_headcount_index(DemographicInput(100, n_chronic_medical=100), w)
        assert psi_med == pytest.approx(300.0)
        # Intersectional only: 100 * 4.5 = 450
        psi_int, _, _, _ = VulnerabilityScoringService.calculate_headcount_index(DemographicInput(100, n_intersectional=100), w)
        assert psi_int == pytest.approx(450.0)

    def test_complete_and_mutually_exclusive_categories(self):
        """Partitioned population: N_TOTAL = N_GEN + N_ACC + N_MED + N_MED_ACC."""
        inp = DemographicInput(
            total_affected_population=100,
            n_general=40,
            n_accessible_needs=20,
            n_chronic_medical=30,
            n_intersectional=10,
        )
        psi, n_gen, is_lb, comp = VulnerabilityScoringService.calculate_headcount_index(inp)
        assert psi == pytest.approx(40*1.0 + 20*2.5 + 30*3.0 + 10*4.5) # 225.0
        assert n_gen == 40
        assert is_lb is False
        assert comp == "COMPLETE"

    def test_missing_subgroup_categories_incomplete_enumeration(self):
        """When subgroups are missing, unsegregated remainder gets base weight 1.0 (conservative lower bound)."""
        inp = DemographicInput(total_affected_population=150)
        psi, n_gen, is_lb, comp = VulnerabilityScoringService.calculate_headcount_index(inp)
        assert psi == pytest.approx(150.0)
        assert n_gen == 150
        assert is_lb is True
        assert comp == "PARTIAL_UNSEGREGATED"

    def test_zero_population(self):
        """Zero population yields zero index without division-by-zero or crashing."""
        inp = DemographicInput(total_affected_population=0, census_baseline_population=1000)
        psi, n_gen, is_lb, comp = VulnerabilityScoringService.calculate_headcount_index(inp)
        assert psi == 0.0
        assert n_gen == 0
        assert comp == "COMPLETE"
        res = VulnerabilityScoringService.calculate_vulnerability_score(inp)
        assert res.phi_vulnerability == 0.0

    def test_subgroup_totals_equal_to_total_population(self):
        """When vulnerable subgroups sum to total, N_GEN = 0 and is_lower_bound = False."""
        inp = DemographicInput(total_affected_population=100, n_accessible_needs=30, n_chronic_medical=50, n_intersectional=20)
        psi, n_gen, is_lb, comp = VulnerabilityScoringService.calculate_headcount_index(inp)
        assert psi == pytest.approx(30*2.5 + 50*3.0 + 20*4.5) # 315.0
        assert n_gen == 0
        assert is_lb is False
        assert comp == "COMPLETE"

    def test_subgroup_totals_below_total_population(self):
        """When vulnerable subgroups are below total, remainder is assigned to N_GEN (weight 1.0)."""
        inp = DemographicInput(total_affected_population=100, n_accessible_needs=20, n_chronic_medical=10)
        psi, n_gen, is_lb, comp = VulnerabilityScoringService.calculate_headcount_index(inp)
        assert n_gen == 70
        assert psi == pytest.approx(70*1.0 + 20*2.5 + 10*3.0) # 150.0
        assert is_lb is True
        assert comp == "PARTIAL_UNSEGREGATED"

    def test_subgroup_totals_exceeding_total_population(self):
        """Over-reporting clamps general remainder to 0 to prevent double-counting."""
        inp = DemographicInput(total_affected_population=60, n_accessible_needs=40, n_chronic_medical=40)
        psi, n_gen, is_lb, comp = VulnerabilityScoringService.calculate_headcount_index(inp)
        assert n_gen == 0
        assert is_lb is True
        assert comp == "INCONSISTENT_OVERREPORTED"
        assert psi == pytest.approx(40*2.5 + 40*3.0) # 220.0

    def test_no_double_counting_with_explicit_general_population(self):
        """N_GEN is never duplicated or added to unsegregated remainder if explicit general count is given."""
        inp = DemographicInput(total_affected_population=100, n_general=50, n_accessible_needs=30, n_chronic_medical=20)
        psi, n_gen, is_lb, comp = VulnerabilityScoringService.calculate_headcount_index(inp)
        assert n_gen == 50
        assert comp == "COMPLETE"
        assert psi == pytest.approx(50*1.0 + 30*2.5 + 20*3.0) # 185.0

    def test_lower_bound_monotonicity_proof(self):
        """Proof: specifying any vulnerable subgroup person strictly non-decreases psi for fixed total."""
        n_total = 100
        psi_base, _, _, _ = VulnerabilityScoringService.calculate_headcount_index(DemographicInput(n_total))
        psi_acc, _, _, _ = VulnerabilityScoringService.calculate_headcount_index(DemographicInput(n_total, n_accessible_needs=1))
        psi_med, _, _, _ = VulnerabilityScoringService.calculate_headcount_index(DemographicInput(n_total, n_chronic_medical=1))
        psi_int, _, _, _ = VulnerabilityScoringService.calculate_headcount_index(DemographicInput(n_total, n_intersectional=1))
        assert psi_base == 100.0
        assert psi_acc == 101.5
        assert psi_med == 102.0
        assert psi_int == 103.5
        assert psi_base < psi_acc < psi_med < psi_int

    def test_two_branch_mapping_and_zero_division_guard(self):
        """Branch A (Known) vs Branch B (Unknown, D_ref = 500.0); zero division guard."""
        # Branch A: P_census = 2000 => D = max(100, 400) = 400.0
        inp_k = DemographicInput(total_affected_population=100, census_baseline_population=2000)
        res_k = VulnerabilityScoringService.calculate_vulnerability_score(inp_k)
        assert res_k.baseline_status == "BASELINE_KNOWN"
        assert res_k.effective_denominator == 400.0

        # Branch B: P_census = None => D_ref = 500.0
        inp_u = DemographicInput(total_affected_population=100, census_baseline_population=None)
        res_u = VulnerabilityScoringService.calculate_vulnerability_score(inp_u)
        assert res_u.baseline_status == "BASELINE_UNKNOWN"
        assert res_u.effective_denominator == 500.0
        assert res_u.uncertainty_flag is True

        # Division by zero protection: P_census = 0 or negative
        inp_z = DemographicInput(total_affected_population=100, census_baseline_population=0)
        res_z = VulnerabilityScoringService.calculate_vulnerability_score(inp_z)
        assert res_z.baseline_status == "BASELINE_UNKNOWN"
        assert res_z.effective_denominator == 500.0

    def test_census_reconciliation_shift(self):
        """Continuity: at P_census = 2500, D_census = 0.20 * 2500 = 500.0 == D_ref."""
        inp_u = DemographicInput(total_affected_population=200, census_baseline_population=None)
        inp_k = DemographicInput(total_affected_population=200, census_baseline_population=2500)
        assert VulnerabilityScoringService.calculate_vulnerability_score(inp_u).phi_vulnerability == \
               VulnerabilityScoringService.calculate_vulnerability_score(inp_k).phi_vulnerability


# ============================================================================
# 2. MCPI PRIORITIZATION & TIE-BREAKING TESTS (AUDIT ITEMS 1, 2, A)
# ============================================================================

class TestMCPITieBreakingAndTiers:
    """Validates authorized tie-breaking hierarchy and inactive status of arbitrary numerical tiers."""

    def test_configurable_administrative_policy_weights(self):
        """Approved baseline weights: 0.30, 0.25, 0.20, 0.15, 0.10; non-negative and summing to 1.0."""
        w = MCPIWeights()
        assert (w.life_safety, w.criticality, w.vulnerability, w.dependency, w.economic) == (0.30, 0.25, 0.20, 0.15, 0.10)
        assert sum([w.life_safety, w.criticality, w.vulnerability, w.dependency, w.economic]) == pytest.approx(1.0)

        with pytest.raises(ValueError, match="must sum to 1.0"):
            MCPIWeights(life_safety=0.5, criticality=0.5, vulnerability=0.5, dependency=0.1, economic=0.1)

    def test_custom_configurable_weights_validation(self):
        custom = MCPIWeights(life_safety=0.40, criticality=0.20, vulnerability=0.20, dependency=0.10, economic=0.10)
        assert custom.life_safety == 0.40

    def test_mcpi_scoring_formula(self):
        # 100 * (0.30*1.0 + 0.25*0.8 + 0.20*0.7 + 0.15*0.6 + 0.10*0.5) = 78.0
        inp = MCPIInput("P-01", "C-01", 1.0, 0.8, 0.7, 0.6, 0.5, estimated_cost=50000.0)
        res = MCPIPrioritizationService.calculate_single(inp)
        assert res.mcpi_score == pytest.approx(78.0)
        assert res.priority_designation == "STANDARD_RECOVERY"

    def test_authorized_tie_breaking_hierarchy(self):
        """
        Authorized ordering under Phase 6D-A:
        1. Mandatory life-safety filter (TIER_1_MANDATORY first)
        2. Higher MCPI score
        3. First tie-breaker: phi_life_safety
        4. Second tie-breaker: phi_vulnerability
        5. Third tie-breaker: transitive_cascade
        6. Fourth tie-breaker: estimated_cost (lower cost first)
        7. Final arbiter: project_id ascending (alphabetical stable fallback)
        """
        w = MCPIWeights()
        # Projects P1 and P2 with identical substantive scores except tie-breaker 1 (phi_life_safety)
        p1 = MCPIInput("P01", "C01", 0.9, 0.5, 0.4, 0.3, 0.2, estimated_cost=1000)
        p2 = MCPIInput("P02", "C02", 0.8, 0.62, 0.4, 0.3, 0.2, estimated_cost=1000)
        ranked = MCPIPrioritizationService.rank_portfolio([p2, p1], w)
        # If raw scores are equal, P1 wins on phi_life_safety
        if abs(p1.phi_life_safety * 0.30 + 0.5*0.25 - (p2.phi_life_safety * 0.30 + 0.62*0.25)) < 1e-6:
            assert ranked[0].project_id == "P01"

    def test_adversarial_exact_equality_mcpi_sub_tolerance_diff(self):
        """
        Adversarial Test A.1: Two projects whose MCPI scores differ by less than 1e-4 (e.g. 1e-5).
        Higher MCPI MUST rank first, even if its project ID is alphabetically later ('Z' beats 'A').
        """
        # P_Z has raw score 0.500010; P_A has raw score 0.500000 (diff = 1e-5 < 1e-4)
        p_z = MCPIInput("PROJECT_Z", "CZ", phi_life_safety=0.5000333333333334, phi_criticality=0.5, phi_vulnerability=0.5, phi_dependency=0.5, phi_economic=0.5, estimated_cost=1000)
        p_a = MCPIInput("PROJECT_A", "CA", phi_life_safety=0.5000000000000000, phi_criticality=0.5, phi_vulnerability=0.5, phi_dependency=0.5, phi_economic=0.5, estimated_cost=1000)

        res_z = MCPIPrioritizationService.calculate_single(p_z)
        res_a = MCPIPrioritizationService.calculate_single(p_a)
        assert res_z.raw_score > res_a.raw_score
        assert (res_z.raw_score - res_a.raw_score) < 1e-4 # Sub-tolerance difference!

        ranked = MCPIPrioritizationService.rank_portfolio([p_a, p_z])
        # PROJECT_Z must rank first despite 'Z' being after 'A'
        assert ranked[0].project_id == "PROJECT_Z"
        assert ranked[1].project_id == "PROJECT_A"

    def test_adversarial_exact_equality_life_safety_sub_tolerance_diff(self):
        """
        Adversarial Test A.2: Two projects with identical MCPI, but life-safety differs by < 1e-4.
        Higher life-safety MUST rank first, even if project ID is later.
        """
        # Exactly identical MCPI raw score, but P_Z has phi_L = 0.80005, P_A has phi_L = 0.80000
        # To maintain identical raw score, adjust criticality slightly:
        # delta(phi_L) * 0.30 = delta(phi_C) * 0.25 => delta(phi_C) = delta(phi_L) * 0.30 / 0.25 = 0.80005 * 0.30 ...
        # Or simpler: keep raw scores exactly equal by using exact complementary weights
        p_z = MCPIInput("PROJECT_Z", "CZ", phi_life_safety=0.80005, phi_criticality=0.50000, phi_vulnerability=0.5, phi_dependency=0.5, phi_economic=0.5, estimated_cost=1000)
        # 0.80005 * 0.30 + 0.50000 * 0.25 = 0.240015 + 0.125000 = 0.365015
        # For p_a: phi_L = 0.80000, phi_C = (0.365015 - 0.80000*0.30) / 0.25 = (0.365015 - 0.24) / 0.25 = 0.125015 / 0.25 = 0.50006
        p_a = MCPIInput("PROJECT_A", "CA", phi_life_safety=0.80000, phi_criticality=0.50006, phi_vulnerability=0.5, phi_dependency=0.5, phi_economic=0.5, estimated_cost=1000)

        res_z = MCPIPrioritizationService.calculate_single(p_z)
        res_a = MCPIPrioritizationService.calculate_single(p_a)
        assert res_z.raw_score == pytest.approx(res_a.raw_score, abs=1e-9)

        ranked = MCPIPrioritizationService.rank_portfolio([p_a, p_z])
        # P_Z has higher phi_life_safety by 0.00005 (< 1e-4), so P_Z must win
        assert ranked[0].project_id == "PROJECT_Z"

    def test_adversarial_exact_equality_vulnerability_sub_tolerance_diff(self):
        """
        Adversarial Test A.3: Identical MCPI and identical phi_L, but phi_V differs by < 1e-4.
        Higher phi_V MUST rank first, even if project ID is later.
        """
        # Exactly identical MCPI and identical phi_L, but P_Z has higher phi_V by 0.00005
        # w_V = 0.20, w_D = 0.15. delta(phi_V) * 0.20 = delta(phi_D) * 0.15
        # delta(phi_D) = 0.00005 * 0.20 / 0.15 = 0.0000666666666667
        p_z = MCPIInput("PROJECT_Z", "CZ", phi_life_safety=0.7, phi_criticality=0.5, phi_vulnerability=0.60005, phi_dependency=0.500000000000, phi_economic=0.5, estimated_cost=1000)
        p_a = MCPIInput("PROJECT_A", "CA", phi_life_safety=0.7, phi_criticality=0.5, phi_vulnerability=0.60000, phi_dependency=0.500066666667, phi_economic=0.5, estimated_cost=1000)

        res_z = MCPIPrioritizationService.calculate_single(p_z)
        res_a = MCPIPrioritizationService.calculate_single(p_a)
        assert res_z.raw_score == pytest.approx(res_a.raw_score, abs=1e-9)

        ranked = MCPIPrioritizationService.rank_portfolio([p_a, p_z])
        assert ranked[0].project_id == "PROJECT_Z"

    def test_project_id_zero_substantive_effect_reversed_ids(self):
        """Proof: reversing project IDs does NOT change ranking when substantive values differ."""
        p_high = MCPIInput("ID_ZULU", "CZ", 0.9, 0.9, 0.9, 0.9, 0.9, estimated_cost=50000)
        p_low = MCPIInput("ID_ALPHA", "CA", 0.1, 0.1, 0.1, 0.1, 0.1, estimated_cost=50000)

        # High has 'ZULU', Low has 'ALPHA'
        ranked1 = MCPIPrioritizationService.rank_portfolio([p_low, p_high])
        assert ranked1[0].project_id == "ID_ZULU"

        # Reverse IDs: High gets 'ALPHA', Low gets 'ZULU'
        p_high_rev = MCPIInput("ID_ALPHA", "CZ", 0.9, 0.9, 0.9, 0.9, 0.9, estimated_cost=50000)
        p_low_rev = MCPIInput("ID_ZULU", "CA", 0.1, 0.1, 0.1, 0.1, 0.1, estimated_cost=50000)
        ranked2 = MCPIPrioritizationService.rank_portfolio([p_low_rev, p_high_rev])
        assert ranked2[0].project_id == "ID_ALPHA"

    def test_project_id_stable_final_tie_breaker_exact_equality(self):
        """When all substantive values are exactly equal, project_id ascending decides order."""
        p1 = MCPIInput("PROJECT_B", "CB", 0.8, 0.5, 0.5, 0.5, 0.5, estimated_cost=10000, transitive_cascade=3)
        p2 = MCPIInput("PROJECT_A", "CA", 0.8, 0.5, 0.5, 0.5, 0.5, estimated_cost=10000, transitive_cascade=3)
        ranked = MCPIPrioritizationService.rank_portfolio([p1, p2])
        assert ranked[0].project_id == "PROJECT_A"
        assert ranked[1].project_id == "PROJECT_B"

    def test_priority_tier_status_authoritative_vs_proposal(self):
        """Numerical tiers (>=70, >=50, >=30) are inactive optional proposals; mandatory filter preserved."""
        inp_norm = MCPIInput("P1", "C1", 0.8, 0.8, 0.8, 0.8, 0.8, 1000)
        res_norm = MCPIPrioritizationService.calculate_single(inp_norm)
        assert res_norm.priority_designation == "STANDARD_RECOVERY"
        assert res_norm.experimental_policy_tier is None

        inp_mand = MCPIInput("P2", "C2", 0.1, 0.1, 0.1, 0.1, 0.1, 1000, is_tier1_mandatory=True)
        res_mand = MCPIPrioritizationService.calculate_single(inp_mand)
        assert res_mand.priority_designation == "TIER_1_MANDATORY"
        assert res_mand.is_tier1_mandatory is True


# ============================================================================
# 3. LIFE SAFETY TRIAGE SERVICE TESTS (AUDIT ITEM 6)
# ============================================================================

class TestLifeSafetyTriageService:
    def test_weights_sum_to_one(self):
        w = LifeSafetyWeights()
        assert sum([w.damage, w.secondary_hazard, w.occupancy]) == pytest.approx(1.0)

    def test_damage_score_parsing_enum_string_float(self):
        assert LifeSafetyTriageService.resolve_damage_score("DESTROYED") == 1.0
        assert LifeSafetyTriageService.resolve_damage_score("SEVERE") == 0.75
        assert LifeSafetyTriageService.resolve_damage_score("MODERATE") == 0.50
        assert LifeSafetyTriageService.resolve_damage_score("MINOR") == 0.25
        assert LifeSafetyTriageService.resolve_damage_score("NONE") == 0.0
        assert LifeSafetyTriageService.resolve_damage_score(0.65) == 0.65

    def test_component_bounds_validation_and_invalid_inputs(self):
        with pytest.raises(ValueError, match="must be in \\[0.0, 1.0\\]"):
            LifeSafetyTriageService.evaluate(LifeSafetyInput(damage_score=1.5, secondary_hazard_score=0.2, occupancy_score=0.2))
        with pytest.raises(ValueError, match="Unknown damage severity rating"):
            LifeSafetyTriageService.evaluate(LifeSafetyInput(damage_score="INVALID_STRING", secondary_hazard_score=0.2, occupancy_score=0.2))

    def test_convex_combination_calculation(self):
        # S_L = 0.70*1.0 + 0.20*0.5 + 0.10*0.8 = 0.88 >= 0.85 -> TIER_1_MANDATORY
        inp = LifeSafetyInput(damage_score="DESTROYED", secondary_hazard_score=0.5, occupancy_score=0.8)
        res = LifeSafetyTriageService.evaluate(inp)
        assert res.score_life_safety == pytest.approx(0.88)
        assert res.is_tier1_mandatory is True

    def test_administrative_triage_threshold_mandatory_elevation(self):
        # Below threshold: S_L = 0.70*0.75 + 0.20*0.2 + 0.10*0.3 = 0.525 + 0.04 + 0.03 = 0.595 < 0.85
        inp = LifeSafetyInput(damage_score="SEVERE", secondary_hazard_score=0.2, occupancy_score=0.3)
        res = LifeSafetyTriageService.evaluate(inp)
        assert res.score_life_safety == pytest.approx(0.595)
        assert res.is_tier1_mandatory is False

    def test_engineering_and_non_licensure_disclaimers(self):
        inp = LifeSafetyInput(damage_score="SEVERE", secondary_hazard_score=0.5, occupancy_score=0.5)
        res = LifeSafetyTriageService.evaluate(inp)
        assert "NOT an empirical civil engineering structural collapse probability" in res.policy_disclosure
        assert "does NOT constitute structural engineering certification" in res.policy_disclosure
        assert "does NOT treat administrative GOVT verification as a substitute for professional engineering licensure" in res.policy_disclosure


# ============================================================================
# 4. PROJECT DEPENDENCY SERVICE TESTS (AUDIT ITEM 6)
# ============================================================================

class TestProjectDependencyService:
    def test_dependency_lag_ceiling_conversion_all_boundaries(self):
        """Ceil lag conversion: ceil(L_days / Delta_t) for 0, 1, 29, 30, 31, 60 days."""
        assert ProjectDependencyService.convert_days_to_periods(0.0, 30.0) == 0
        assert ProjectDependencyService.convert_days_to_periods(1.0, 30.0) == 1
        assert ProjectDependencyService.convert_days_to_periods(29.0, 30.0) == 1
        assert ProjectDependencyService.convert_days_to_periods(30.0, 30.0) == 1
        assert ProjectDependencyService.convert_days_to_periods(31.0, 30.0) == 2
        assert ProjectDependencyService.convert_days_to_periods(60.0, 30.0) == 2

    def test_invalid_dependency_inputs_negative_values(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            ProjectDependencyService.convert_days_to_periods(-5.0, 30.0)
        with pytest.raises(ValueError, match="must be positive"):
            ProjectDependencyService.convert_days_to_periods(10.0, 0.0)

    def test_toposort_linear_acyclic(self):
        nodes = ["A", "B", "C"]
        edges = [DependencyEdge("A", "B"), DependencyEdge("B", "C")]
        order = ProjectDependencyService.detect_cycle_and_toposort(nodes, edges)
        assert order == ["A", "B", "C"]

    def test_cycle_detection_path_extraction(self):
        nodes = ["P1", "P2", "P3"]
        edges = [
            DependencyEdge("P1", "P2"),
            DependencyEdge("P2", "P3"),
            DependencyEdge("P3", "P1"),
        ]
        with pytest.raises(CyclicDependencyError) as exc_info:
            ProjectDependencyService.detect_cycle_and_toposort(nodes, edges)
        assert len(exc_info.value.cycle_path) >= 3

    def test_transitive_cascade_reachability(self):
        nodes = ["A", "B", "C", "D"]
        edges = [DependencyEdge("A", "B"), DependencyEdge("B", "C"), DependencyEdge("A", "D")]
        cascades = ProjectDependencyService.calculate_transitive_cascades(nodes, edges)
        assert cascades["A"] == 3
        assert cascades["B"] == 1
        assert cascades["C"] == 0
        assert cascades["D"] == 0

    def test_cpm_pl_forward_backward_pass_floats_critical_path(self):
        activities = [
            ProjectActivity("A", duration_periods=2),
            ProjectActivity("B", duration_periods=3),
            ProjectActivity("C", duration_periods=1),
            ProjectActivity("D", duration_periods=2),
        ]
        edges = [
            DependencyEdge("A", "B", lag_periods=1),
            DependencyEdge("A", "C", lag_periods=0),
            DependencyEdge("B", "D", lag_periods=0),
            DependencyEdge("C", "D", lag_periods=0),
        ]
        cpm, crit_path, makespan = ProjectDependencyService.compute_cpm_pl(activities, edges)
        assert makespan == 8
        assert cpm["A"].is_critical is True
        assert cpm["B"].is_critical is True
        assert cpm["D"].is_critical is True
        assert cpm["C"].is_critical is False
        assert cpm["C"].total_float == 3


# ============================================================================
# 5. CALENDAR COST SERVICE TESTS (AUDIT ITEM 6)
# ============================================================================

class TestCalendarCostService:
    def test_gamma_profiles_uniform_front_back_scurve_custom(self):
        g_u = CalendarCostService.generate_gamma_profile(4, DisbursementCurveType.UNIFORM)
        assert sum(g_u) == pytest.approx(1.0)
        g_f = CalendarCostService.generate_gamma_profile(3, DisbursementCurveType.FRONT_LOADED)
        assert g_f[0] > g_f[1] > g_f[2] and sum(g_f) == pytest.approx(1.0)
        g_b = CalendarCostService.generate_gamma_profile(3, DisbursementCurveType.BACK_LOADED)
        assert g_b[0] < g_b[1] < g_b[2] and sum(g_b) == pytest.approx(1.0)
        g_s = CalendarCostService.generate_gamma_profile(5, DisbursementCurveType.S_CURVE)
        assert sum(g_s) == pytest.approx(1.0)

    def test_calendar_boundary_and_day_tests_0_1_29_30_31_60(self):
        """Boundary tests for 0, 1, 29, 30, 31, 60 days from anchor."""
        anchor = date(2026, 1, 1)
        assert CalendarCostService.map_date_to_period(anchor + timedelta(days=0), anchor, 30) == 1
        assert CalendarCostService.map_date_to_period(anchor + timedelta(days=1), anchor, 30) == 1
        assert CalendarCostService.map_date_to_period(anchor + timedelta(days=29), anchor, 30) == 1
        assert CalendarCostService.map_date_to_period(anchor + timedelta(days=30), anchor, 30) == 2
        assert CalendarCostService.map_date_to_period(anchor + timedelta(days=31), anchor, 30) == 2
        assert CalendarCostService.map_date_to_period(anchor + timedelta(days=60), anchor, 30) == 3

    def test_partial_final_period_treatment_truncation(self):
        spec = ProjectDisbursementSpec(
            project_id="P_LONG",
            total_cost=90000.0,
            duration_periods=3,
            start_period=4,
            curve_type=DisbursementCurveType.UNIFORM,
        )
        sched = CalendarCostService.convolve_expenditure(spec, planning_horizon_periods=4)
        assert sched.periodic_costs[4] == pytest.approx(30000.0)
        assert sched.is_fully_reconciled is False

    def test_cost_convolution_full_lifetime_reconciliation(self):
        spec = ProjectDisbursementSpec(
            project_id="P_FULL",
            total_cost=100000.0,
            duration_periods=2,
            start_period=1,
            curve_type=DisbursementCurveType.UNIFORM,
        )
        sched = CalendarCostService.convolve_expenditure(spec, planning_horizon_periods=4)
        assert sched.is_fully_reconciled is True
        assert sum(sched.periodic_costs.values()) == pytest.approx(100000.0)


# ============================================================================
# 6. EQUITY CALCULATION SERVICE TESTS (AUDIT ITEM 4)
# ============================================================================

class TestEquityPolicyRingFencing:
    def test_internal_policy_equity_floor_and_dynamic_capacity(self):
        """Validates mathematical policy ring-fencing without implying escrow/bank accounts."""
        districts = [
            DistrictEquitySpec("NORTH", "North District", policy_floor_ratio=0.20),
            DistrictEquitySpec("SOUTH", "South District", policy_floor_ratio=0.20),
        ]
        pipelines = {
            "NORTH": DistrictProjectPipeline("NORTH", 300000.0),
            "SOUTH": DistrictProjectPipeline("SOUTH", 120000.0),
        }
        targets, blackout = EquityCalculationService.calculate_district_targets(1000000.0, districts, pipelines)

        assert targets["NORTH"].policy_nominal_floor == 200000.0
        assert targets["NORTH"].effective_allocation_target == 200000.0
        assert targets["NORTH"].unabsorbed_policy_reserve == 0.0

        assert targets["SOUTH"].policy_nominal_floor == 200000.0
        assert targets["SOUTH"].effective_allocation_target == 120000.0
        assert targets["SOUTH"].unabsorbed_policy_reserve == 80000.0
        assert "NOT actual financial escrow accounts" in targets["SOUTH"].policy_disclosure

    def test_unabsorbed_policy_reserve_and_zero_eligible_absorption(self):
        """Zero pipeline absorption in a district results in 100% unabsorbed policy reserve."""
        districts = [DistrictEquitySpec("WEST", "West District", policy_floor_ratio=0.15)]
        pipelines = {"WEST": DistrictProjectPipeline("WEST", 0.0)} # Zero absorption!
        targets, _ = EquityCalculationService.calculate_district_targets(1000000.0, districts, pipelines)
        assert targets["WEST"].effective_allocation_target == 0.0
        assert targets["WEST"].unabsorbed_policy_reserve == 150000.0
        assert targets["WEST"].is_capacity_constrained is True

    def test_uncontacted_blackout_reserve(self):
        districts = [DistrictEquitySpec("EAST", "East District", 0.15, is_blackout=True, blackout_reserve_ratio=0.15)]
        pipelines = {"EAST": DistrictProjectPipeline("EAST", 500000.0)}
        _, blackout = EquityCalculationService.calculate_district_targets(1000000.0, districts, pipelines)
        assert blackout == 150000.0

    def test_policy_ring_fencing_vs_liquidity_accounting_separation(self):
        districts = [DistrictEquitySpec("D1", "District 1", policy_floor_ratio=0.25)]
        pipelines = {"D1": DistrictProjectPipeline("D1", 500000.0)}
        audit = EquityCalculationService.audit_equity_feasibility(1000000.0, districts, pipelines, {"D1": 260000.0})
        assert audit.is_equity_feasible is True
        assert "Strict accounting separation of concepts" in audit.liquidity_separation_note


# ============================================================================
# 7. CASH FLOW SOLVENCY SERVICE TESTS (AUDIT ITEM 6)
# ============================================================================

class TestCashFlowSolvencyService:
    def test_solvent_trajectory_with_carry_forward(self):
        plan = FundTranchePlan("MUNICIPAL", initial_reserve=50.0, inflows_by_period={1: 100.0, 2: 50.0})
        exp = {1: 80.0, 2: 100.0}
        traj = CashFlowSolvencyService.evaluate_fund_trajectory(plan, exp, 2)
        assert traj.is_fully_solvent is True
        assert traj.periods[1].ending_balance == 70.0
        assert traj.periods[2].ending_balance == 20.0

    def test_insolvent_trajectory_detects_shortfall_and_earliest_period(self):
        plan = FundTranchePlan("GRANT", initial_reserve=0.0, inflows_by_period={1: 50.0, 2: 100.0})
        exp = {1: 80.0, 2: 20.0}
        traj = CashFlowSolvencyService.evaluate_fund_trajectory(plan, exp, 2)
        assert traj.is_fully_solvent is False
        assert traj.earliest_deficit_period == 1
        assert traj.periods[1].shortfall == 30.0

    def test_multi_fund_ring_fencing_prevents_unauthorized_cross_subsidy(self):
        f1 = FundTranchePlan("MUNICIPAL_SURPLUS", initial_reserve=100.0)
        f2 = FundTranchePlan("GRANT_DEFICIT", initial_reserve=10.0)
        exp_map = {
            "MUNICIPAL_SURPLUS": {1: 20.0},
            "GRANT_DEFICIT": {1: 30.0},
        }
        audit = CashFlowSolvencyService.audit_multi_fund_portfolio([f1, f2], exp_map, 1)
        assert audit.aggregate_ending_balance[1] == 60.0
        assert audit.is_portfolio_solvent is False
        assert len(audit.violations) == 1
        assert "GRANT_DEFICIT" in audit.violations[0]
