import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.recovery import RecoveryNeed, RecoveryAssessment
from app.schemas.recovery import (
    PopulationReconciliationRequest,
    PopulationReconciliationResponse,
    DuplicateCandidateGroup,
    UnresolvedConflictItem
)


class PopulationReconciliationService:
    """
    Phase 6C Population and Household Reconciliation Service.
    Transparently reconciles affected populations, identifies duplicate beneficiary
    observations, detects assessment conflicts, and verifies totals against census caps
    without double-counting.
    """

    @classmethod
    def reconcile_population(
        cls,
        db: Session,
        request: PopulationReconciliationRequest
    ) -> PopulationReconciliationResponse:
        """
        Executes multi-record reconciliation across recovery needs in a target administrative area.
        """
        q = db.query(RecoveryNeed)
        if request.ward_code:
            q = q.filter(RecoveryNeed.ward_code == request.ward_code)
        if request.district:
            q = q.filter(RecoveryNeed.district == request.district)
        if request.need_ids:
            q = q.filter(RecoveryNeed.id.in_(request.need_ids))

        needs: List[RecoveryNeed] = q.all()

        source_record_count = len(needs)
        if source_record_count == 0:
            return PopulationReconciliationResponse(
                ward_code=request.ward_code or "ALL",
                district=request.district or "ALL",
                source_record_count=0,
                unique_beneficiary_count=0,
                reconciled_affected_households=0,
                reconciled_displaced_persons=0,
                reconciled_demographics={"gen": 0, "acc": 0, "med": 0, "med_acc": 0, "total": 0},
                census_baseline_population=0,
                census_utilization_pct=0.0,
                duplicate_candidates=[],
                unresolved_conflicts=[],
                reconciliation_status="EMPTY",
                confidence_score=100.0,
                provenance_summary="No records matched reconciliation criteria"
            )

        # 1. Group records by beneficiary_id_hash
        beneficiary_groups: Dict[str, List[RecoveryNeed]] = {}
        unhashed_needs: List[RecoveryNeed] = []

        for n in needs:
            if n.beneficiary_id_hash:
                beneficiary_groups.setdefault(n.beneficiary_id_hash, []).append(n)
            else:
                unhashed_needs.append(n)

        # 2. Identify duplicate candidate groups and conflicts
        duplicate_candidates: List[DuplicateCandidateGroup] = []
        unresolved_conflicts: List[UnresolvedConflictItem] = []

        reconciled_hh_count = 0
        reconciled_disp_count = 0
        reconciled_gen = 0
        reconciled_acc = 0
        reconciled_med = 0
        reconciled_med_acc = 0

        # Process hashed groups
        for b_hash, group in beneficiary_groups.items():
            if len(group) > 1:
                # Duplicate candidate identified
                sample = group[0]
                masked_name = sample.household_head_name_masked or "Unknown"
                matched_ids = [item.id for item in group]
                duplicate_candidates.append(
                    DuplicateCandidateGroup(
                        beneficiary_hash=b_hash,
                        matched_need_ids=matched_ids,
                        household_head_name_masked=masked_name,
                        record_count=len(group),
                        match_reason="Exact salted HMAC-SHA256 beneficiary identifier match"
                    )
                )

                # Check if group has conflicting counts
                hh_counts = set(item.affected_households for item in group)
                disp_counts = set(item.displaced_persons for item in group)
                if len(hh_counts) > 1 or len(disp_counts) > 1:
                    unresolved_conflicts.append(
                        UnresolvedConflictItem(
                            cluster_id=f"CONF-{b_hash[:8]}",
                            conflicting_need_ids=matched_ids,
                            reason=f"Conflicting affected/displaced counts reported for same beneficiary: HH={list(hh_counts)}, Displaced={list(disp_counts)}",
                            requires_human_review=True
                        )
                    )

                # Deduplication strategy: Use latest verified or maximum observation
                chosen = max(group, key=lambda x: (x.is_reconciled, x.data_timestamp or datetime.min))
            else:
                chosen = group[0]

            reconciled_hh_count += chosen.affected_households
            reconciled_disp_count += chosen.displaced_persons

            # Parse demographics
            try:
                meta = json.loads(chosen.reconciliation_notes or "{}")
                dem = meta.get("demographics", {})
            except Exception:
                dem = {}

            reconciled_gen += dem.get("gen", chosen.affected_households * 3)
            reconciled_acc += dem.get("acc", 0)
            reconciled_med += dem.get("med", 0)
            reconciled_med_acc += dem.get("med_acc", 0)

        # Process unhashed needs (e.g. ward-level aggregated reports)
        for n in unhashed_needs:
            reconciled_hh_count += n.affected_households
            reconciled_disp_count += n.displaced_persons
            try:
                meta = json.loads(n.reconciliation_notes or "{}")
                dem = meta.get("demographics", {})
            except Exception:
                dem = {}
            reconciled_gen += dem.get("gen", n.affected_households * 3)
            reconciled_acc += dem.get("acc", 0)
            reconciled_med += dem.get("med", 0)
            reconciled_med_acc += dem.get("med_acc", 0)

        total_reconciled_pop = reconciled_gen + reconciled_acc + reconciled_med + reconciled_med_acc

        # 3. Census baseline comparison
        census_baseline = max(n.census_baseline_population for n in needs)
        utilization_pct = round((total_reconciled_pop / census_baseline * 100.0), 2) if census_baseline > 0 else 0.0

        if utilization_pct > 100.0:
            unresolved_conflicts.append(
                UnresolvedConflictItem(
                    cluster_id="CONF-CENSUS-OVERCAP",
                    conflicting_need_ids=[n.id for n in needs],
                    reason=f"Reconciled affected population ({total_reconciled_pop}) exceeds ward census baseline cap ({census_baseline}) by {utilization_pct - 100.0:.1f}%",
                    requires_human_review=True
                )
            )

        unique_beneficiaries = len(beneficiary_groups) + len(unhashed_needs)

        # 4. Determine overall status & confidence
        if len(unresolved_conflicts) > 0:
            status_val = "FLAGGED_FOR_HUMAN_REVIEW"
            confidence = max(50.0, 100.0 - (len(unresolved_conflicts) * 15.0))
        elif len(duplicate_candidates) > 0:
            status_val = "RECONCILED_DEDUPLICATED"
            confidence = 90.0
        else:
            status_val = "FULLY_RECONCILED"
            confidence = 98.0

        prov = (
            f"Reconciliation evaluated {source_record_count} records across {unique_beneficiaries} unique entities. "
            f"Detected {len(duplicate_candidates)} duplicate candidate clusters and {len(unresolved_conflicts)} unresolved conflicts."
        )

        return PopulationReconciliationResponse(
            ward_code=request.ward_code or "AGGREGATED",
            district=request.district or "AGGREGATED",
            source_record_count=source_record_count,
            unique_beneficiary_count=unique_beneficiaries,
            reconciled_affected_households=reconciled_hh_count,
            reconciled_displaced_persons=reconciled_disp_count,
            reconciled_demographics={
                "gen": reconciled_gen,
                "acc": reconciled_acc,
                "med": reconciled_med,
                "med_acc": reconciled_med_acc,
                "total": total_reconciled_pop
            },
            census_baseline_population=census_baseline,
            census_utilization_pct=utilization_pct,
            duplicate_candidates=duplicate_candidates,
            unresolved_conflicts=unresolved_conflicts,
            reconciliation_status=status_val,
            confidence_score=round(confidence, 1),
            provenance_summary=prov
        )
