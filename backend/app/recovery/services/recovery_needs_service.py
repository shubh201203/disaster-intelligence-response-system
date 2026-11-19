import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.recovery import RecoveryNeed, RecoveryAssessment
from app.schemas.recovery import (
    StructuredRecoveryNeedCreate,
    StructuredRecoveryNeedResponse
)
from app.core.security import hash_beneficiary_id, mask_person_name
from app.services.audit_service import AuditService


class RecoveryNeedsService:
    """
    Phase 6C Recovery Needs Intelligence Service.
    Enforces structured multi-sectoral needs with Phase 6A demographic conservation:
    total_affected = GEN + ACC + MED + MED_ACC,
    non-negative constraints, salted beneficiary pseudonymization, and census baseline capping.
    """

    VALID_SECTORS = {"HOUSING", "WASH", "HEALTH", "EDUCATION", "LIVELIHOODS", "ESSENTIAL_SERVICES", "POWER", "TRANSPORT"}

    @classmethod
    def create_structured_need(
        cls,
        db: Session,
        data: StructuredRecoveryNeedCreate,
        user_id: str
    ) -> StructuredRecoveryNeedResponse:
        """
        Creates a structured recovery need record with strict demographic conservation.
        """
        # Validate sector
        sector_clean = data.sector.upper()
        if sector_clean not in cls.VALID_SECTORS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sector '{data.sector}'. Allowed sectors: {sorted(list(cls.VALID_SECTORS))}"
            )

        # Non-negative validation
        if (data.affected_population_gen < 0 or
            data.affected_population_acc < 0 or
            data.affected_population_med < 0 or
            data.affected_population_med_acc < 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Demographic population figures cannot be negative"
            )

        if data.affected_households < 0 or data.displaced_persons < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Household and displaced counts cannot be negative"
            )

        # Enforce Demographic Conservation
        total_affected = (
            data.affected_population_gen +
            data.affected_population_acc +
            data.affected_population_med +
            data.affected_population_med_acc
        )

        if data.displaced_persons > total_affected and total_affected > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Displaced persons ({data.displaced_persons}) cannot exceed total affected population ({total_affected})"
            )

        # Validate linked assessment if provided
        if data.assessment_id:
            asm = db.query(RecoveryAssessment).filter(RecoveryAssessment.id == data.assessment_id).first()
            if not asm:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Linked assessment {data.assessment_id} not found"
                )

        # Salted Beneficiary Pseudonymization and PII Masking
        b_hash = None
        masked_name = None
        if data.raw_beneficiary_id:
            b_hash = hash_beneficiary_id(data.raw_beneficiary_id)
        if data.raw_household_head_name:
            masked_name = mask_person_name(data.raw_household_head_name)

        # Census Baseline Check
        census_cap = data.census_baseline_population
        if census_cap <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Census baseline population must be greater than zero"
            )

        exceeds_census = total_affected > census_cap

        demographic_dict = {
            "gen": data.affected_population_gen,
            "acc": data.affected_population_acc,
            "med": data.affected_population_med,
            "med_acc": data.affected_population_med_acc,
            "total_affected": total_affected,
            "exceeds_census_cap": exceeds_census
        }

        reconciliation_metadata = {
            "demographics": demographic_dict,
            "urgency_tier": data.urgency_tier.upper(),
            "time_horizon_days": data.time_horizon_days,
            "is_verified_demand": data.is_verified_demand,
            "source_confidence": data.source_confidence,
            "notes": data.notes or ""
        }

        # Calculate vulnerable persons sum (ACC + MED + MED_ACC)
        vulnerable_total = data.affected_population_acc + data.affected_population_med + data.affected_population_med_acc

        need = RecoveryNeed(
            assessment_id=data.assessment_id,
            ward_code=data.ward_code,
            district=data.district,
            sector=sector_clean,
            affected_households=data.affected_households,
            displaced_persons=data.displaced_persons,
            vulnerable_persons=vulnerable_total,
            beneficiary_id_hash=b_hash,
            household_head_name_masked=masked_name,
            potable_water_demand_liters_day=data.potable_water_demand_liters_day,
            temporary_shelter_units_needed=data.temporary_shelter_units_needed,
            livelihood_support_households=data.livelihood_support_households,
            unmet_need_score=data.unmet_need_score,
            census_baseline_population=census_cap,
            is_reconciled=False,
            reconciliation_notes=json.dumps(reconciliation_metadata),
            data_timestamp=datetime.now(timezone.utc)
        )
        db.add(need)
        db.commit()
        db.refresh(need)

        AuditService.log_action(
            db,
            user_id=user_id,
            action="CREATE_STRUCTURED_NEED",
            target_entity="RecoveryNeed",
            details={
                "ward_code": need.ward_code,
                "sector": need.sector,
                "total_affected": total_affected,
                "exceeds_census": exceeds_census
            }
        )

        return cls._map_to_response(need, demographic_dict, reconciliation_metadata)

    @classmethod
    def list_structured_needs(
        cls,
        db: Session,
        sector: Optional[str] = None,
        ward_code: Optional[str] = None,
        district: Optional[str] = None
    ) -> List[StructuredRecoveryNeedResponse]:
        """
        Queries structured recovery needs with filtering. Non-privileged roles
        cannot access raw beneficiary identity information.
        """
        q = db.query(RecoveryNeed)
        if sector:
            q = q.filter(RecoveryNeed.sector == sector.upper())
        if ward_code:
            q = q.filter(RecoveryNeed.ward_code == ward_code)
        if district:
            q = q.filter(RecoveryNeed.district == district)

        needs = q.order_by(RecoveryNeed.data_timestamp.desc()).all()
        results = []
        for n in needs:
            try:
                meta = json.loads(n.reconciliation_notes or "{}")
            except Exception:
                meta = {}
            demographics = meta.get("demographics", {
                "gen": n.affected_households * 4,
                "acc": 0,
                "med": 0,
                "med_acc": 0,
                "total_affected": n.affected_households * 4
            })
            results.append(cls._map_to_response(n, demographics, meta))
        return results

    @classmethod
    def _map_to_response(
        cls,
        need: RecoveryNeed,
        demographics: Dict[str, Any],
        meta: Dict[str, Any]
    ) -> StructuredRecoveryNeedResponse:
        return StructuredRecoveryNeedResponse(
            id=need.id,
            assessment_id=need.assessment_id,
            ward_code=need.ward_code,
            district=need.district,
            sector=need.sector,
            affected_households=need.affected_households,
            displaced_persons=need.displaced_persons,
            vulnerable_persons=need.vulnerable_persons,
            affected_population_gen=demographics.get("gen", 0),
            affected_population_acc=demographics.get("acc", 0),
            affected_population_med=demographics.get("med", 0),
            affected_population_med_acc=demographics.get("med_acc", 0),
            total_affected_population=demographics.get("total_affected", 0),
            beneficiary_id_hash=need.beneficiary_id_hash,
            household_head_name_masked=need.household_head_name_masked,
            potable_water_demand_liters_day=need.potable_water_demand_liters_day,
            temporary_shelter_units_needed=need.temporary_shelter_units_needed,
            livelihood_support_households=need.livelihood_support_households,
            unmet_need_score=need.unmet_need_score,
            census_baseline_population=need.census_baseline_population,
            exceeds_census_cap=demographics.get("exceeds_census_cap", False),
            urgency_tier=meta.get("urgency_tier", "MEDIUM_TIER3"),
            time_horizon_days=meta.get("time_horizon_days", 30),
            is_verified_demand=meta.get("is_verified_demand", False),
            source_confidence=meta.get("source_confidence", 100.0),
            is_reconciled=need.is_reconciled,
            data_timestamp=need.data_timestamp
        )
