import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session

from app.models.recovery import RecoveryProject, RecoveryResource, RecoveryNeed
from app.schemas.recovery import (
    RecoveryWhatIfSimulationRequest,
    RecoveryWhatIfSimulationResponse,
    SimulationPeriodSnapshot,
    BottleneckResourceItem,
    SimulationPerturbationParams
)


class RecoverySimulationService:
    """
    Phase 6F / Accelerated Programme WP2: What-If Recovery Scenario Simulation Engine.
    
    Guarantees:
    - 100% Read-Only / Non-Mutating (Zero database writes, no session commit).
    - Deterministic forward state projection across planning horizon T.
    - Sensitivity analysis over budget multipliers, resource supply shocks,
      and secondary hazard recurrence events.
    """

    PROTOTYPICAL_PROJECTS = [
        {
            "id": "SIM-PRJ-01",
            "title": "Ward 4 Water Purification Station Rehabilitation",
            "sector": "WASH",
            "estimated_cost": 2500000.0,
            "duration_periods": 2,
            "displaced_reduction": 150,
            "recovery_contribution": 20.0,
            "materials": {"PIPING": 40.0, "CEMENT": 60.0}
        },
        {
            "id": "SIM-PRJ-02",
            "title": "Central District Hospital Emergency Wing Restructure",
            "sector": "HEALTH",
            "estimated_cost": 4000000.0,
            "duration_periods": 3,
            "displaced_reduction": 200,
            "recovery_contribution": 25.0,
            "materials": {"STRUCTURAL_STEEL": 80.0, "HEAVY_MACHINERY": 30.0}
        },
        {
            "id": "SIM-PRJ-03",
            "title": "East Zone Power Grid Transmission Tower Repair",
            "sector": "POWER",
            "estimated_cost": 3000000.0,
            "duration_periods": 2,
            "displaced_reduction": 100,
            "recovery_contribution": 25.0,
            "materials": {"STRUCTURAL_STEEL": 50.0, "WORKFORCE": 100.0}
        },
        {
            "id": "SIM-PRJ-04",
            "title": "Community Primary Schools Seismic Retrofitting",
            "sector": "EDUCATION",
            "estimated_cost": 1800000.0,
            "duration_periods": 2,
            "displaced_reduction": 80,
            "recovery_contribution": 15.0,
            "materials": {"CEMENT": 80.0, "TIMBER": 40.0}
        },
        {
            "id": "SIM-PRJ-05",
            "title": "Artisanal Fishery & Market Livelihoods Hub",
            "sector": "LIVELIHOODS",
            "estimated_cost": 1500000.0,
            "duration_periods": 1,
            "displaced_reduction": 120,
            "recovery_contribution": 15.0,
            "materials": {"TIMBER": 50.0, "WORKFORCE": 80.0}
        },
    ]

    @classmethod
    def simulate_what_if(
        cls,
        db: Session,
        req: RecoveryWhatIfSimulationRequest
    ) -> RecoveryWhatIfSimulationResponse:
        """
        Executes in-memory what-if simulation comparing baseline vs perturbed scenario.
        Strictly non-mutating.
        """
        # 1. Gather Candidate Projects from DB (read-only query)
        q = db.query(RecoveryProject)
        if req.candidate_project_ids:
            q = q.filter(RecoveryProject.id.in_(req.candidate_project_ids))
        
        db_projects: List[RecoveryProject] = q.all()

        candidates: List[Dict[str, Any]] = []
        if db_projects:
            for p in db_projects:
                # Compute duration in planning periods
                dur_periods = max(1, math.ceil((p.estimated_duration_days or 30) / req.period_length_days))
                cost = float(p.estimated_cost or 1000000.0)
                # Map resources if any
                mat_dict: Dict[str, float] = {}
                for res in (p.resources or []):
                    cat = res.material_category or "GENERAL"
                    mat_dict[cat] = mat_dict.get(cat, 0.0) + float(res.quantity_required or 0.0)
                if not mat_dict:
                    mat_dict = {"CEMENT": 50.0, "WORKFORCE": 50.0}

                candidates.append({
                    "id": p.id,
                    "title": p.title,
                    "sector": p.sector,
                    "estimated_cost": cost,
                    "duration_periods": dur_periods,
                    "displaced_reduction": 100,
                    "recovery_contribution": 15.0,
                    "materials": mat_dict
                })
        else:
            candidates = [dict(cp) for cp in cls.PROTOTYPICAL_PROJECTS]

        # 2. Run Baseline Simulation (nominal multipliers: budget=1.0, supply=1.0, no shock)
        baseline_nominal_params = SimulationPerturbationParams(
            budget_multiplier=1.0,
            material_supply_factor=1.0,
            disaster_recurrence_shock=False,
            shock_period=req.perturbation.shock_period,
            shock_damage_factor=0.0,
            sector_priorities={}
        )
        base_snapshots, base_comp_per, base_final_score, _ = cls._run_simulation_loop(
            req=req,
            params=baseline_nominal_params,
            candidates=candidates
        )

        # 3. Run Perturbed / Simulated Scenario
        sim_snapshots, sim_comp_per, sim_final_score, bottlenecks = cls._run_simulation_loop(
            req=req,
            params=req.perturbation,
            candidates=candidates
        )

        # 4. Compute Periods to 80% Target
        target_period: Optional[int] = None
        for snap in sim_snapshots:
            if snap.projected_recovery_score >= 80.0:
                target_period = snap.period
                break

        # Compute Financial Totals
        tot_budget_alloc = req.initial_budget * req.perturbation.budget_multiplier + (
            req.periodic_budget_inflow * req.perturbation.budget_multiplier * req.planning_horizon_periods
        )
        tot_spent = sim_snapshots[-1].cumulative_capital_spent if sim_snapshots else 0.0
        tot_project_cost = sum(c["estimated_cost"] for c in candidates)
        deficit = max(0.0, tot_project_cost - tot_budget_alloc)

        prov = {
            "is_non_mutating": True,
            "candidate_count": len(candidates),
            "source": "DATABASE_RECORDS" if db_projects else "STANDARDIZED_PROTOTYPES",
            "perturbation_applied": req.perturbation.model_dump(),
            "simulation_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return RecoveryWhatIfSimulationResponse(
            scenario_name=req.scenario_name,
            planning_horizon_periods=req.planning_horizon_periods,
            period_length_days=req.period_length_days,
            is_non_mutating=True,
            baseline_completion_period=base_comp_per,
            simulated_completion_period=sim_comp_per,
            baseline_final_recovery_score=base_final_score,
            simulated_final_recovery_score=sim_final_score,
            recovery_score_delta=round(sim_final_score - base_final_score, 2),
            periods_to_target_80pct=target_period,
            total_budget_allocated=round(tot_budget_alloc, 2),
            total_budget_utilized=round(tot_spent, 2),
            unmet_budget_deficit=round(deficit, 2),
            bottleneck_resources=bottlenecks,
            trajectory=sim_snapshots,
            simulation_provenance=prov
        )

    @classmethod
    def _run_simulation_loop(
        cls,
        req: RecoveryWhatIfSimulationRequest,
        params: SimulationPerturbationParams,
        candidates: List[Dict[str, Any]]
    ) -> tuple[List[SimulationPeriodSnapshot], Optional[int], float, List[BottleneckResourceItem]]:
        """
        Pure in-memory step simulation over T planning periods.
        """
        snapshots: List[SimulationPeriodSnapshot] = []
        
        # Sort candidates by priority (sector priority multiplier * inverse cost ratio)
        def candidate_priority(c: Dict[str, Any]) -> float:
            prio = params.sector_priorities.get(c["sector"], 1.0)
            return prio * (c["recovery_contribution"] / max(1.0, c["estimated_cost"]))

        sorted_candidates = sorted(candidates, key=candidate_priority, reverse=True)

        # Simulation State
        remaining_cash = req.initial_budget * params.budget_multiplier
        cum_spent = 0.0
        completed_ids: Set[str] = set()
        in_flight: Dict[str, Dict[str, Any]] = {}  # prj_id -> {periods_left, cost_per_period, candidate}
        unstarted = list(sorted_candidates)

        initial_displaced = sum(c["displaced_reduction"] for c in candidates) * 3
        current_displaced = initial_displaced
        current_score = 0.0
        completion_period: Optional[int] = None

        # Material tracking
        mat_demands: Dict[str, float] = {}
        for c in candidates:
            for m, q in c.get("materials", {}).items():
                mat_demands[m] = mat_demands.get(m, 0.0) + q

        # Resource bottlenecks tracking
        bottlenecks: List[BottleneckResourceItem] = []
        for m, dem in mat_demands.items():
            avail = dem * params.material_supply_factor
            if avail < dem:
                deficit = dem - avail
                lvl = "HIGH" if (deficit / dem) > 0.3 else "MODERATE"
                bottlenecks.append(BottleneckResourceItem(
                    material_category=m,
                    demand_quantity=round(dem, 1),
                    available_supply=round(avail, 1),
                    deficit_quantity=round(deficit, 1),
                    impact_level=lvl
                ))

        for t in range(1, req.planning_horizon_periods + 1):
            shock_occurred_this_period = False
            # Periodic cash inflow
            periodic_inflow = req.periodic_budget_inflow * params.budget_multiplier
            remaining_cash += periodic_inflow

            # Check for disaster recurrence shock
            if params.disaster_recurrence_shock and t == params.shock_period:
                shock_occurred_this_period = True
                # Delay all in-flight projects by shock damage factor
                for p_id, infl in in_flight.items():
                    extra_periods = max(1, math.ceil(infl["periods_left"] * params.shock_damage_factor))
                    infl["periods_left"] += extra_periods
                # Displaced population surges
                current_displaced = int(current_displaced * (1.0 + params.shock_damage_factor))
                # Slight recovery score regression
                current_score = max(0.0, current_score * (1.0 - params.shock_damage_factor * 0.5))

            # Progress in-flight projects
            period_spent = 0.0
            just_completed: List[str] = []
            for p_id, infl in list(in_flight.items()):
                cost_this_period = infl["cost_per_period"]
                if remaining_cash >= cost_this_period:
                    remaining_cash -= cost_this_period
                    period_spent += cost_this_period
                    infl["periods_left"] -= 1
                    if infl["periods_left"] <= 0:
                        just_completed.append(p_id)
                else:
                    # Cash starved: project stalled this period
                    pass

            for p_id in just_completed:
                cand = in_flight[p_id]["candidate"]
                completed_ids.add(p_id)
                del in_flight[p_id]
                current_score = min(100.0, current_score + cand["recovery_contribution"])
                current_displaced = max(0, current_displaced - cand["displaced_reduction"] * 3)

            # Start new projects if cash and capacity permit
            # Supply bottleneck slows down starts
            start_capacity = max(1, int(4 * params.material_supply_factor))
            new_unstarted: List[Dict[str, Any]] = []
            for cand in unstarted:
                if len(in_flight) >= start_capacity:
                    new_unstarted.append(cand)
                    continue

                dur = cand["duration_periods"]
                cost_per_p = cand["estimated_cost"] / dur
                if remaining_cash >= cost_per_p:
                    remaining_cash -= cost_per_p
                    period_spent += cost_per_p
                    in_flight[cand["id"]] = {
                        "periods_left": dur - 1,
                        "cost_per_period": cost_per_p,
                        "candidate": cand
                    }
                    if dur - 1 <= 0:
                        completed_ids.add(cand["id"])
                        del in_flight[cand["id"]]
                        current_score = min(100.0, current_score + cand["recovery_contribution"])
                        current_displaced = max(0, current_displaced - cand["displaced_reduction"] * 3)
                else:
                    new_unstarted.append(cand)

            unstarted = new_unstarted
            cum_spent += period_spent

            if len(completed_ids) == len(candidates) and completion_period is None:
                completion_period = t

            # Unmet needs score: complement of recovery score
            unmet_score = round(max(0.0, 100.0 - current_score), 2)

            snapshot = SimulationPeriodSnapshot(
                period=t,
                calendar_day=round(t * req.period_length_days, 1),
                capital_spent_period=round(period_spent, 2),
                cumulative_capital_spent=round(cum_spent, 2),
                remaining_cash_balance=round(remaining_cash, 2),
                projects_in_progress=len(in_flight),
                projects_completed_cumulative=len(completed_ids),
                displaced_persons_remaining=current_displaced,
                projected_recovery_score=round(current_score, 2),
                unmet_needs_score=unmet_score,
                shock_occurred=shock_occurred_this_period
            )
            snapshots.append(snapshot)

        return snapshots, completion_period, round(current_score, 2), bottlenecks
