from datetime import datetime, timezone
from typing import Dict, Any
import numpy as np
from app.ai.severity.features import extract_features_from_dict
from app.ai.severity.model import load_trained_severity_model
from app.ai.severity.explainer import generate_severity_explanation
from app.ai.common.confidence import ConfidenceEvaluator
from app.ai.common.schemas import SeverityPredictionResponse

class SeverityPredictor:
    def __init__(self):
        self.model = load_trained_severity_model()
        self.model_name = "severity-classifier-rf"
        self.model_version = "1.0.0"

    def predict(self, incident_id: str, incident_data: Dict[str, Any]) -> SeverityPredictionResponse:
        features = extract_features_from_dict(incident_data)
        features_2d = features.reshape(1, -1)
        
        prediction = self.model.predict(features_2d)[0]
        
        # Probabilities & Confidence
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(features_2d)[0]
            confidence = float(np.max(probs)) * 100.0
        else:
            confidence = 85.0
            
        requires_review = ConfidenceEvaluator.evaluate(confidence)
        factors = generate_severity_explanation(features, prediction, confidence)
        
        return SeverityPredictionResponse(
            incident_id=incident_id,
            prediction=str(prediction),
            confidence=round(confidence, 1),
            requires_human_review=requires_review,
            model_name=self.model_name,
            model_version=self.model_version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            factors=factors
        )
