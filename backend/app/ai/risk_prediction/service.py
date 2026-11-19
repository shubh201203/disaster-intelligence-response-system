import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.incident import Incident
from app.models.ai import RiskAssessment, AIPrediction
from app.models.user import User
from app.ai.risk_prediction.features import extract_risk_features, RISK_LEVELS
from app.ai.risk_prediction.model import load_trained_risk_model
from app.ai.risk_prediction.explainer import generate_risk_explanation
from app.ai.common.confidence import ConfidenceEvaluator

class RiskPredictionService:
    @classmethod
    def calculate_risk(
        cls,
        db: Session,
        incident: Optional[Incident] = None,
        environmental_data: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        Calculates geographic/meteorological disaster risk score (0-100), risk level (LOW, MODERATE, HIGH, EXTREME),
        confidence, and factor contributions. Persists to risk_assessments and ai_predictions DB tables.
        """
        data = environmental_data or {}
        if incident:
            data.setdefault("disaster_type", incident.disaster_type)
            data.setdefault("population_exposure", incident.people_affected * 25.0 + 500.0)
            if incident.disaster_type == "FLOOD":
                data.setdefault("rainfall_mm", 120.0 if incident.people_affected > 20 else 45.0)
                data.setdefault("river_level_m", 3.8 if incident.people_affected > 20 else 1.5)
            elif incident.disaster_type == "CYCLONE":
                data.setdefault("wind_speed_kmh", 110.0 if incident.people_affected > 20 else 55.0)

        features = extract_risk_features(data)
        features_2d = features.reshape(1, -1)

        model = load_trained_risk_model()
        pred_level = str(model.predict(features_2d)[0])
        probs = model.predict_proba(features_2d)[0]
        prob_dict = {cls_name: float(p) for cls_name, p in zip(model.classes_, probs)}
        confidence = float(np.max(probs) * 100.0)

        # 0-100 Risk Score mapping based on class probability weights & inputs
        base_score = float(
            (prob_dict.get("LOW", 0.0) * 15.0) +
            (prob_dict.get("MODERATE", 0.0) * 40.0) +
            (prob_dict.get("HIGH", 0.0) * 70.0) +
            (prob_dict.get("EXTREME", 0.0) * 95.0)
        )
        risk_score = round(min(100.0, max(0.0, base_score)), 1)

        requires_review = ConfidenceEvaluator.evaluate(confidence)
        factors = generate_risk_explanation(features, risk_score, pred_level)

        factors_list = [f.model_dump() for f in factors]

        assessment = RiskAssessment(
            incident_id=incident.id if incident else None,
            geographic_scope=str(data.get("geographic_scope", "District Central Zone")),
            disaster_type=str(data.get("disaster_type", incident.disaster_type if incident else "FLOOD")),
            risk_score=risk_score,
            risk_level=pred_level,
            confidence=round(confidence, 2),
            requires_human_review=requires_review,
            input_snapshot=data,
            contributing_factors=factors_list,
            model_version="1.0.0"
        )
        db.add(assessment)

        # Also persist to immutable AIPrediction log table
        ai_pred = AIPrediction(
            entity_type="Incident" if incident else "GeographicZone",
            entity_id=incident.id if incident else "ZONE-CENTRAL",
            prediction_type="RISK_PREDICTION",
            model_name="risk-prediction-rf",
            model_version="1.0.0",
            prediction=f"{risk_score} ({pred_level})",
            confidence=round(confidence, 2),
            requires_human_review=requires_review,
            explanation={"risk_score": risk_score, "factors": factors_list},
            input_snapshot=data
        )
        db.add(ai_pred)

        db.commit()
        db.refresh(assessment)
        return assessment

    @classmethod
    def override_risk_assessment(
        cls,
        db: Session,
        assessment_id: str,
        override_level: str,
        notes: str,
        reviewer: User
    ) -> RiskAssessment:
        """
        Allows authorized Government Officers to review and override AI risk predictions.
        Preserves original AI output while recording reviewer identity and notes.
        """
        assessment = db.query(RiskAssessment).filter(RiskAssessment.id == assessment_id).first()
        if not assessment:
            raise ValueError("Risk assessment not found")

        override_clean = override_level.upper()
        if override_clean not in RISK_LEVELS:
            raise ValueError(f"Invalid risk level '{override_level}'. Allowed: {RISK_LEVELS}")

        assessment.is_overridden = True
        assessment.override_level = override_clean
        assessment.override_notes = notes
        assessment.reviewer_id = reviewer.id
        assessment.requires_human_review = False

        db.commit()
        db.refresh(assessment)
        return assessment
