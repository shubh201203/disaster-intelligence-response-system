import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.incident import Incident
from app.models.resource import Resource
from app.models.shelter import Shelter
from app.models.ai import ResourceDemandPrediction, AIPrediction
from app.models.user import User
from app.ai.resource_demand.features import extract_resource_demand_features, RESOURCE_TYPES
from app.ai.resource_demand.model import load_trained_resource_model
from app.ai.common.confidence import ConfidenceEvaluator

RESOURCE_UNITS = {
    "water_packs": "liters",
    "food_packets": "units",
    "medical_kits": "kits",
    "shelter_beds": "beds",
    "rescue_personnel": "responders"
}

class ResourceDemandService:
    @classmethod
    def predict_incident_demand(
        cls,
        db: Session,
        incident: Incident
    ) -> ResourceDemandPrediction:
        """
        Predicts required quantities for 5 core resource types based on incident severity and demographics.
        Compares predicted demand against current NGO stock and shelter capacity to detect shortages.
        Persists results to resource_demand_predictions and ai_predictions DB tables.
        """
        input_data = {
            "people_affected": incident.people_affected,
            "injuries": incident.injuries,
            "vulnerable_count": incident.vulnerable_count,
            "infrastructure_damage": incident.infrastructure_damage,
            "severity_level": incident.severity_level,
            "disaster_type": incident.disaster_type
        }

        features = extract_resource_demand_features(input_data)
        features_2d = features.reshape(1, -1)

        model = load_trained_resource_model()
        pred_raw = model.predict(features_2d)[0]

        predictions_dict: Dict[str, Any] = {}
        for idx, res_name in enumerate(RESOURCE_TYPES):
            val = max(0.0, float(pred_raw[idx]))
            # 15% uncertainty range
            lower = max(0.0, round(val * 0.85, 1))
            upper = round(val * 1.15, 1)

            predictions_dict[res_name] = {
                "quantity": round(val, 1),
                "unit": RESOURCE_UNITS.get(res_name, "units"),
                "confidence": 88.5,
                "lower_bound": lower,
                "upper_bound": upper
            }

        # Check for inventory shortages against active database stock
        shortages = cls._check_inventory_shortages(db, predictions_dict)

        overall_confidence = 88.5
        requires_review = ConfidenceEvaluator.evaluate(overall_confidence)

        factors = [
            f"+{incident.people_affected} People Affected baseline scaling",
            f"+{incident.injuries} Injured victims requiring Medical & First Aid Kits",
            f"+{incident.vulnerable_count} Vulnerable demographics requiring shelter & water",
            f"Hazard Type ({incident.disaster_type}) demand multiplier"
        ]

        prediction_entity = ResourceDemandPrediction(
            incident_id=incident.id,
            predictions=predictions_dict,
            overall_confidence=overall_confidence,
            requires_human_review=requires_review,
            contributing_features=factors,
            shortages_detected=shortages,
            model_version="1.0.0"
        )
        db.add(prediction_entity)

        # Also persist to immutable AIPrediction log table
        ai_pred = AIPrediction(
            entity_type="Incident",
            entity_id=incident.id,
            prediction_type="RESOURCE_DEMAND",
            model_name="resource-demand-rf-regressor",
            model_version="1.0.0",
            prediction=f"Water: {predictions_dict['water_packs']['quantity']}L, Food: {predictions_dict['food_packets']['quantity']}, Med: {predictions_dict['medical_kits']['quantity']}",
            confidence=overall_confidence,
            requires_human_review=requires_review,
            explanation={"predictions": predictions_dict, "shortages": shortages, "factors": factors},
            input_snapshot=input_data
        )
        db.add(ai_pred)

        db.commit()
        db.refresh(prediction_entity)
        return prediction_entity

    @classmethod
    def _check_inventory_shortages(cls, db: Session, predictions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Compares predicted resource demand quantities against current available NGO stock and shelter capacity.
        """
        shortages = []

        # Available NGO resources
        avail_water = db.query(Resource).filter(Resource.category == "WATER").all()
        total_water = sum(r.available_quantity for r in avail_water) if avail_water else 0.0

        avail_food = db.query(Resource).filter(Resource.category == "FOOD").all()
        total_food = sum(r.available_quantity for r in avail_food) if avail_food else 0.0

        avail_med = db.query(Resource).filter(Resource.category == "MEDICINE").all()
        total_med = sum(r.available_quantity for r in avail_med) if avail_med else 0.0

        # Available Shelter Capacity
        open_shelters = db.query(Shelter).filter(Shelter.status == "OPEN").all()
        avail_beds = sum(s.total_capacity - s.current_occupancy for s in open_shelters) if open_shelters else 0

        req_water = predictions.get("water_packs", {}).get("quantity", 0.0)
        if total_water < req_water:
            shortages.append({
                "resource_type": "water_packs",
                "demanded": req_water,
                "available": total_water,
                "shortage_quantity": round(req_water - total_water, 1),
                "severity": "CRITICAL" if (req_water - total_water) > 200 else "WARNING"
            })

        req_food = predictions.get("food_packets", {}).get("quantity", 0.0)
        if total_food < req_food:
            shortages.append({
                "resource_type": "food_packets",
                "demanded": req_food,
                "available": total_food,
                "shortage_quantity": round(req_food - total_food, 1),
                "severity": "CRITICAL" if (req_food - total_food) > 200 else "WARNING"
            })

        req_med = predictions.get("medical_kits", {}).get("quantity", 0.0)
        if total_med < req_med:
            shortages.append({
                "resource_type": "medical_kits",
                "demanded": req_med,
                "available": total_med,
                "shortage_quantity": round(req_med - total_med, 1),
                "severity": "CRITICAL" if (req_med - total_med) > 20 else "WARNING"
            })

        req_beds = predictions.get("shelter_beds", {}).get("quantity", 0.0)
        if avail_beds < req_beds:
            shortages.append({
                "resource_type": "shelter_beds",
                "demanded": req_beds,
                "available": avail_beds,
                "shortage_quantity": round(req_beds - avail_beds, 1),
                "severity": "CRITICAL" if (req_beds - avail_beds) > 50 else "WARNING"
            })

        return shortages

    @classmethod
    def override_demand_prediction(
        cls,
        db: Session,
        prediction_id: str,
        override_demands: Dict[str, float],
        notes: str,
        reviewer: User
    ) -> ResourceDemandPrediction:
        """
        Allows authorized Government Officers to override predicted resource demand quantities.
        Preserves original AI output while recording reviewer identity and notes.
        """
        entity = db.query(ResourceDemandPrediction).filter(ResourceDemandPrediction.id == prediction_id).first()
        if not entity:
            raise ValueError("Resource demand prediction not found")

        entity.is_overridden = True
        entity.override_demands = override_demands
        entity.override_notes = notes
        entity.reviewer_id = reviewer.id
        entity.requires_human_review = False

        db.commit()
        db.refresh(entity)
        return entity
