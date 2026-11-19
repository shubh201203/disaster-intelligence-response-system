import os
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.incident import Incident, IncidentMedia
from app.models.ai import CVDamageAssessment, AIPrediction
from app.models.user import User
from app.ai.computer_vision.features import extract_image_visual_features, DAMAGE_CLASSES
from app.ai.computer_vision.model import load_trained_cv_model
from app.ai.computer_vision.explainer import generate_cv_visual_explanation
from app.ai.common.confidence import ConfidenceEvaluator

class ComputerVisionService:
    @classmethod
    def analyze_incident_image(
        cls,
        db: Session,
        incident: Incident,
        media: Optional[IncidentMedia] = None
    ) -> CVDamageAssessment:
        """
        Analyzes incident evidence image, predicts structural damage class, confidence, and visual explanation.
        Persists results to cv_damage_assessments and ai_predictions DB tables.
        """
        model = load_trained_cv_model()

        # Determine image file path
        file_path = media.file_path if media else ""
        features = extract_image_visual_features(file_path)

        # Model Inference
        features_2d = features.reshape(1, -1)
        pred_class = str(model.predict(features_2d)[0])
        probs = model.predict_proba(features_2d)[0]

        # Calculate confidence & class probabilities
        class_probs = {cls_name: round(float(prob * 100.0), 2) for cls_name, prob in zip(DAMAGE_CLASSES, probs)}
        max_prob = float(np.max(probs) * 100.0)

        # Evaluate human review threshold (< 70% confidence)
        requires_review = ConfidenceEvaluator.evaluate(max_prob)

        # Generate visual explanation
        explanation = generate_cv_visual_explanation(features, pred_class, max_prob)

        # Save CVDamageAssessment entity
        assessment = CVDamageAssessment(
            incident_id=incident.id,
            evidence_id=media.id if media else None,
            damage_class=pred_class,
            confidence=round(max_prob, 2),
            class_probabilities=class_probs,
            model_version="1.0.0",
            requires_human_review=requires_review,
            explanation_metadata=explanation
        )
        db.add(assessment)

        # Also persist to immutable AIPrediction log table
        ai_pred = AIPrediction(
            entity_type="IncidentMedia" if media else "Incident",
            entity_id=media.id if media else incident.id,
            prediction_type="COMPUTER_VISION",
            model_name="cv-damage-classifier-rf",
            model_version="1.0.0",
            prediction=pred_class,
            confidence=round(max_prob, 2),
            requires_human_review=requires_review,
            explanation=explanation,
            input_snapshot={"file_path": file_path, "features": features.tolist()}
        )
        db.add(ai_pred)

        db.commit()
        db.refresh(assessment)
        return assessment

    @classmethod
    def override_damage_assessment(
        cls,
        db: Session,
        assessment_id: str,
        override_class: str,
        notes: str,
        reviewer: User
    ) -> CVDamageAssessment:
        """
        Allows authorized Government Officers to review and override AI CV damage classifications.
        Preserves original AI prediction while marking record as human-overridden.
        """
        assessment = db.query(CVDamageAssessment).filter(CVDamageAssessment.id == assessment_id).first()
        if not assessment:
            raise ValueError("CV damage assessment not found")

        override_class_clean = override_class.upper()
        if override_class_clean not in DAMAGE_CLASSES:
            raise ValueError(f"Invalid damage class '{override_class}'. Allowed: {DAMAGE_CLASSES}")

        assessment.is_overridden = True
        assessment.override_class = override_class_clean
        assessment.override_notes = notes
        assessment.reviewer_id = reviewer.id
        assessment.requires_human_review = False

        db.commit()
        db.refresh(assessment)
        return assessment
