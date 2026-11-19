import os
import uuid
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import numpy as np
from PIL import Image
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

from app.models.incident import Incident
from app.models.user import User
from app.models.ai import CVDamageAssessment, AIPrediction
from app.models.recovery import RecoveryAssessment, RecoveryOverrideLog
from app.schemas.recovery import (
    DamageScreeningRequest,
    DamageScreeningResponse,
    DamageAssessmentFieldCreate,
    RecoveryAssessmentResponse,
    DamageAssessmentVerifyRequest,
    RecoveryAssessmentSupersede,
    DamageAssessmentHistoryResponse
)
from app.ai.computer_vision.features import extract_image_visual_features, DAMAGE_CLASSES, FEATURE_NAMES
from app.ai.computer_vision.model import load_trained_cv_model
from app.ai.computer_vision.explainer import generate_cv_visual_explanation
from app.ai.common.confidence import ConfidenceEvaluator
from app.services.audit_service import AuditService


class DamageAssessmentService:
    """
    Phase 6C Damage Assessment Intelligence Service.
    Integrates frozen Phase 3B Computer Vision inference as a Tier-1 screening tool,
    supports field engineering inspections, multi-tier human verification,
    and monotonic assessment supersession.
    """

    DAMAGE_CLASS_MAPPING = {
        "NO_DAMAGE": "NONE",
        "LOW_DAMAGE": "MINOR",
        "MODERATE_DAMAGE": "MODERATE",
        "SEVERE_DAMAGE": "SEVERE",
        "DESTROYED": "DESTROYED"
    }

    # ==========================================================================
    # 1. TIER-1 AI IMAGE SCREENING (FROZEN PHASE 3B REUSE)
    # ==========================================================================

    @classmethod
    def screen_damage_image(
        cls,
        db: Session,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        incident_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> DamageScreeningResponse:
        """
        Executes Tier-1 screening using frozen Phase 3B CV model.
        Preserves image SHA-256 hash provenance and enforces that output is treated
        as non-certified screening, not certified structural engineering judgment.
        """
        if not image_path and not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either image_path or image_bytes must be provided for CV screening"
            )

        # 1. Calculate image SHA-256 hash
        if image_bytes:
            image_hash = hashlib.sha256(image_bytes).hexdigest()
            # Validate that bytes represent a valid image
            try:
                import io
                with Image.open(io.BytesIO(image_bytes)) as test_img:
                    test_img.verify()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid or corrupted image data: {str(e)}"
                )
            # Save temporary file for feature extraction if path not specified
            temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp_screening")
            os.makedirs(temp_dir, exist_ok=True)
            effective_path = os.path.join(temp_dir, f"{image_hash[:16]}.jpg")
            with open(effective_path, "wb") as f:
                f.write(image_bytes)
        else:
            if not os.path.exists(image_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Image file not found at: {image_path}"
                )
            with open(image_path, "rb") as f:
                image_hash = hashlib.sha256(f.read()).hexdigest()
            effective_path = image_path

        # 2. Extract 6 handcrafted features using frozen Phase 3B pipeline
        features = extract_image_visual_features(effective_path)

        # 3. Model inference using frozen Random Forest / ResNet backbone
        model = load_trained_cv_model()
        features_2d = features.reshape(1, -1)
        pred_class = str(model.predict(features_2d)[0])
        probs = model.predict_proba(features_2d)[0]

        class_probs = {
            cls_name: round(float(prob * 100.0), 2)
            for cls_name, prob in zip(DAMAGE_CLASSES, probs)
        }
        max_prob = float(np.max(probs) * 100.0)

        # 4. Evaluate confidence threshold (< 70% requires human review)
        requires_review = ConfidenceEvaluator.evaluate(max_prob)
        if max_prob < 50.0:
            is_uncertain = True
        else:
            is_uncertain = False

        # 5. Visual explanation
        explanation = generate_cv_visual_explanation(features, pred_class, max_prob)

        # 6. Map to recovery damage level
        mapped_damage_level = cls.DAMAGE_CLASS_MAPPING.get(pred_class, "MODERATE")

        # 7. Persist CVDamageAssessment
        cv_assessment = CVDamageAssessment(
            incident_id=incident_id or "UNKNOWN_INCIDENT",
            evidence_id=None,
            damage_class=pred_class,
            confidence=round(max_prob, 2),
            class_probabilities=class_probs,
            model_version="2.0.0-realworld",
            requires_human_review=requires_review or is_uncertain,
            explanation_metadata={
                "features": {name: round(float(val), 4) for name, val in zip(FEATURE_NAMES, features)},
                "image_sha256": image_hash,
                "explanation": explanation,
                "is_uncertain": is_uncertain
            }
        )
        db.add(cv_assessment)
        db.commit()
        db.refresh(cv_assessment)

        disclaimer = (
            "Tier-1 AI screening only. Certified structural engineering verification "
            "by authorized Government personnel is required before condemning or repairing structures."
        )

        return DamageScreeningResponse(
            cv_assessment_id=cv_assessment.id,
            predicted_damage_class=pred_class,
            mapped_recovery_damage_level=mapped_damage_level,
            confidence_score=round(max_prob, 2),
            class_probabilities=class_probs,
            model_name="cv-damage-classifier-resnet18",
            model_version="2.0.0-realworld",
            requires_human_review=requires_review or is_uncertain,
            is_uncertain=is_uncertain,
            image_sha256=image_hash,
            screening_disclaimer=disclaimer,
            feature_summary={name: round(float(val), 4) for name, val in zip(FEATURE_NAMES, features)}
        )

    # ==========================================================================
    # 2. FIELD DAMAGE ASSESSMENT SUBMISSION
    # ==========================================================================

    @classmethod
    def submit_field_inspection(
        cls,
        db: Session,
        data: DamageAssessmentFieldCreate,
        inspector: User
    ) -> RecoveryAssessment:
        """
        Ingests a formal engineering or field damage inspection.
        Links optional Tier-1 CV screening record, establishes initial version V1,
        and enforces PENDING_VERIFICATION state.
        """
        # Validate incident
        inc = db.query(Incident).filter(Incident.id == data.incident_id).first()
        if not inc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {data.incident_id} not found"
            )

        # Coordinate boundary checks
        if not (-90.0 <= data.latitude <= 90.0) or not (-180.0 <= data.longitude <= 180.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid coordinates: lat={data.latitude}, lon={data.longitude}. Valid range: lat [-90, 90], lon [-180, 180]"
            )

        # Validate linked CV assessment if provided
        if data.cv_assessment_id:
            cv_rec = db.query(CVDamageAssessment).filter(CVDamageAssessment.id == data.cv_assessment_id).first()
            if not cv_rec:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Linked CV assessment {data.cv_assessment_id} not found"
                )

        code = f"ASM-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"

        geom_point = None
        if db.bind and db.bind.dialect.name == "postgresql":
            geom_point = ST_SetSRID(ST_MakePoint(data.longitude, data.latitude), 4326)

        provenance = "TIER_2_GOVT_OFFICIAL" if inspector.role == "GOVT" else "TIER_3_VOLUNTEER_FIELD"

        asm = RecoveryAssessment(
            assessment_code=code,
            incident_id=data.incident_id,
            inspector_id=inspector.id,
            sector=data.sector.upper(),
            facility_name=data.facility_name,
            damage_level=data.damage_level.upper(),
            is_operational=data.is_operational,
            estimated_reconstruction_cost=data.estimated_reconstruction_cost,
            structural_notes=data.structural_notes,
            evidence_media_urls=data.evidence_media_urls or [],
            cv_assessment_id=data.cv_assessment_id,
            latitude=data.latitude,
            longitude=data.longitude,
            geom=geom_point,
            assessment_version=1,
            is_current_version=True,
            deduplication_cluster_id=f"CLUSTER-{uuid.uuid4().hex[:8].upper()}",
            reconciliation_status="UNRECONCILED",
            provenance_tier=provenance,
            data_confidence=data.assessor_confidence if data.assessor_confidence is not None else 100.0,
            freshness_status="FRESH",
            verification_status="PENDING_VERIFICATION",
            created_at=datetime.now(timezone.utc)
        )
        db.add(asm)
        db.commit()
        db.refresh(asm)

        AuditService.log_action(
            db,
            user_id=inspector.id,
            action="CREATE_DAMAGE_ASSESSMENT",
            target_entity="RecoveryAssessment",
            details={
                "code": asm.assessment_code,
                "facility": asm.facility_name,
                "damage_level": asm.damage_level,
                "cv_assessment_id": asm.cv_assessment_id
            }
        )

        return asm

    # ==========================================================================
    # 3. ENGINEERING VERIFICATION GATE (GOVT ONLY)
    # ==========================================================================

    @classmethod
    def verify_damage_assessment(
        cls,
        db: Session,
        assessment_id: str,
        data: DamageAssessmentVerifyRequest,
        verifier: User
    ) -> RecoveryAssessment:
        """
        Allows authorized Government Engineers to certify, dispute, or reject
        a damage assessment. Emits immutable override audit log.
        """
        asm = db.query(RecoveryAssessment).filter(RecoveryAssessment.id == assessment_id).first()
        if not asm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Damage assessment {assessment_id} not found"
            )

        orig_status = asm.verification_status
        orig_damage = asm.damage_level

        action_upper = data.action.upper()
        if action_upper not in ("VERIFY", "REJECT", "DISPUTE"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action '{data.action}'. Allowed: VERIFY, REJECT, DISPUTE"
            )

        if action_upper == "VERIFY":
            asm.verification_status = "VERIFIED"
            if data.verified_damage_level:
                asm.damage_level = data.verified_damage_level.upper()
        elif action_upper == "REJECT":
            asm.verification_status = "REJECTED"
        elif action_upper == "DISPUTE":
            asm.verification_status = "DISPUTED"

        asm.verified_by_id = verifier.id
        asm.verified_at = datetime.now(timezone.utc)
        if data.engineering_notes:
            asm.structural_notes = (asm.structural_notes or "") + f"\n[Engineering Review]: {data.engineering_notes}"

        # Capture audit log
        override_log = RecoveryOverrideLog(
            project_id=None,
            user_id=verifier.id,
            action=f"ASSESSMENT_{action_upper}",
            original_value={"status": orig_status, "damage_level": orig_damage},
            new_value={"status": asm.verification_status, "damage_level": asm.damage_level},
            justification_reason=data.engineering_notes
        )
        db.add(override_log)
        db.commit()
        db.refresh(asm)

        return asm

    # ==========================================================================
    # 4. MONOTONIC VERSIONING & SUPERSESSION HISTORY
    # ==========================================================================

    @classmethod
    def supersede_assessment(
        cls,
        db: Session,
        old_id: str,
        data: RecoveryAssessmentSupersede,
        inspector: User
    ) -> RecoveryAssessment:
        """
        Supersedes an existing assessment monotonically (V_k -> V_{k+1}).
        """
        old_asm = db.query(RecoveryAssessment).filter(RecoveryAssessment.id == old_id).first()
        if not old_asm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
        if not old_asm.is_current_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only supersede an active current-version assessment"
            )

        new_version_num = old_asm.assessment_version + 1
        new_code = f"{old_asm.assessment_code}-V{new_version_num}"

        geom_point = None
        if db.bind and db.bind.dialect.name == "postgresql":
            geom_point = ST_SetSRID(ST_MakePoint(old_asm.longitude, old_asm.latitude), 4326)

        new_asm = RecoveryAssessment(
            assessment_code=new_code,
            incident_id=old_asm.incident_id,
            inspector_id=inspector.id,
            sector=old_asm.sector,
            facility_name=old_asm.facility_name,
            damage_level=data.new_damage_level.upper(),
            is_operational=data.is_operational,
            estimated_reconstruction_cost=data.new_estimated_cost,
            structural_notes=data.structural_notes or old_asm.structural_notes,
            evidence_media_urls=old_asm.evidence_media_urls,
            latitude=old_asm.latitude,
            longitude=old_asm.longitude,
            geom=geom_point,
            assessment_version=new_version_num,
            is_current_version=True,
            deduplication_cluster_id=old_asm.deduplication_cluster_id,
            reconciliation_status="UNRECONCILED",
            provenance_tier="TIER_2_GOVT_OFFICIAL" if inspector.role == "GOVT" else "TIER_3_VOLUNTEER_FIELD",
            data_confidence=old_asm.data_confidence,
            freshness_status="FRESH",
            verification_status="PENDING_VERIFICATION",
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_asm)
        db.flush()

        old_asm.is_current_version = False
        old_asm.superseded_by_id = new_asm.id
        old_asm.reconciliation_status = "SUPERSEDED"

        override_log = RecoveryOverrideLog(
            project_id=None,
            user_id=inspector.id,
            action="ASSESSMENT_SUPERSEDE",
            original_value={"version": old_asm.assessment_version, "damage": old_asm.damage_level, "cost": old_asm.estimated_reconstruction_cost},
            new_value={"version": new_asm.assessment_version, "damage": new_asm.damage_level, "cost": new_asm.estimated_reconstruction_cost},
            justification_reason=data.supersede_reason
        )
        db.add(override_log)

        db.commit()
        db.refresh(new_asm)
        return new_asm

    @classmethod
    def get_assessment_history(
        cls,
        db: Session,
        assessment_id: str
    ) -> DamageAssessmentHistoryResponse:
        """
        Retrieves complete chronological version lineage for an assessment.
        """
        target = db.query(RecoveryAssessment).filter(RecoveryAssessment.id == assessment_id).first()
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

        cluster_id = target.deduplication_cluster_id
        if cluster_id:
            all_versions = db.query(RecoveryAssessment).filter(
                RecoveryAssessment.deduplication_cluster_id == cluster_id
            ).order_by(RecoveryAssessment.assessment_version.asc()).all()
        else:
            all_versions = [target]

        versions_data = []
        for v in all_versions:
            versions_data.append({
                "id": v.id,
                "assessment_code": v.assessment_code,
                "version": v.assessment_version,
                "is_current": v.is_current_version,
                "damage_level": v.damage_level,
                "estimated_cost": v.estimated_reconstruction_cost,
                "verification_status": v.verification_status,
                "verified_by_id": v.verified_by_id,
                "inspector_id": v.inspector_id,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "cv_assessment_id": v.cv_assessment_id
            })

        return DamageAssessmentHistoryResponse(
            facility_name=target.facility_name,
            cluster_id=cluster_id or target.id,
            current_version=target.assessment_version if target.is_current_version else max(v["version"] for v in versions_data),
            total_versions=len(versions_data),
            version_lineage=versions_data
        )
