import json
import os
from typing import Dict, List, Optional
from app.ai.common.schemas import ModelRegistryItem

class ModelRegistry:
    _registry: Dict[str, ModelRegistryItem] = {}

    @classmethod
    def register(cls, item: ModelRegistryItem) -> None:
        cls._registry[item.name] = item

    @classmethod
    def get(cls, name: str) -> Optional[ModelRegistryItem]:
        return cls._registry.get(name)

    @classmethod
    def list_models(cls) -> List[ModelRegistryItem]:
        return list(cls._registry.values())

# Pre-register initial models for Phase 3A/3B compatibility
ModelRegistry.register(
    ModelRegistryItem(
        name="severity-classifier-rf",
        version="1.0.0",
        purpose="Classifies disaster incident severity into LOW, MEDIUM, HIGH, CRITICAL",
        framework="Scikit-Learn (RandomForestClassifier)",
        dataset="Development Synthetic Disaster Dataset v1 (1,000 samples)",
        training_date="2026-09-10",
        status="RETIRED",
        metrics={
            "accuracy": 0.945,
            "macro_f1": 0.942,
            "critical_recall": 0.965,
            "high_recall": 0.938
        },
        limitations="Trained on synthetic development dataset; replaced by v2.0.0-realworld."
    )
)

ModelRegistry.register(
    ModelRegistryItem(
        name="priority-scoring-engine",
        version="1.0.0",
        purpose="Calculates transparent 0-100 incident priority score based on weighted multi-factor scoring",
        framework="Python Deterministic Rule Engine",
        dataset="N/A (Rule-based Expert System)",
        training_date="2026-09-10",
        status="ACTIVE",
        metrics={"predictability": 1.0, "explainability": 1.0},
        limitations="Relies on accurate initial citizen demographic reporting."
    )
)

ModelRegistry.register(
    ModelRegistryItem(
        name="spatio-temporal-duplicate-detector",
        version="1.0.0",
        purpose="Identifies candidate duplicate incident reports using spatial distance, time delta, and text similarity",
        framework="Python Spatial Haversine + Scikit-Learn TF-IDF Cosine Similarity",
        dataset="N/A (Spatio-Temporal Similarity Heuristic)",
        training_date="2026-09-10",
        status="ACTIVE",
        metrics={"recall": 0.92, "precision": 0.88},
        limitations="Recommends candidates only; never auto-deletes reports without human government review."
    )
)

ModelRegistry.register(
    ModelRegistryItem(
        name="cv-damage-classifier-rf",
        version="1.0.0",
        purpose="Classifies structural damage severity (NO_DAMAGE to DESTROYED) from incident evidence photos",
        framework="Python PIL Visual Feature Extractor + Scikit-Learn (RandomForestClassifier)",
        dataset="Synthetic Visual Feature Dataset v1 (1,000 samples)",
        training_date="2026-09-15",
        status="RETIRED",
        metrics={"accuracy": 1.0, "macro_f1": 1.0, "severe_recall": 1.0, "destroyed_recall": 1.0},
        limitations="Demonstration proxy pipeline; replaced by v2.0.0-realworld."
    )
)

ModelRegistry.register(
    ModelRegistryItem(
        name="risk-prediction-rf",
        version="1.0.0",
        purpose="Predicts geographic meteorological disaster risk score (0-100) and risk level (LOW to EXTREME)",
        framework="Scikit-Learn (RandomForestClassifier)",
        dataset="Synthetic Meteorological Dataset v1 (2,000 samples)",
        training_date="2026-09-15",
        status="RETIRED",
        metrics={"accuracy": 1.0, "macro_f1": 1.0, "high_recall": 1.0, "extreme_recall": 1.0},
        limitations="Trained on synthetic scenario distributions; replaced by v2.0.0-realworld."
    )
)

ModelRegistry.register(
    ModelRegistryItem(
        name="resource-demand-rf-regressor",
        version="1.0.0",
        purpose="Predicts required relief resource quantities (water, food, medical kits, beds, personnel)",
        framework="Scikit-Learn (Multi-Output RandomForestRegressor)",
        dataset="Synthetic Resource Demand Dataset v1 (2,000 samples)",
        training_date="2026-09-15",
        status="RETIRED",
        metrics={"mae": 2.15, "rmse": 3.40, "r2": 0.998},
        limitations="Regresses demand from reported casualties; replaced by Sphere-calibrated model."
    )
)

# Register Phase 4 Active Real-World Models
ModelRegistry.register(
    ModelRegistryItem(
        name="severity-classifier-gb-realworld",
        version="2.0.0-realworld",
        purpose="Classifies incident severity into LOW, MEDIUM, HIGH, CRITICAL based on derived Composite Impact Index S_impact",
        framework="Scikit-Learn (GradientBoostingClassifier)",
        dataset="OpenFEMA IA/PA + CrisisNLP Corpus (5,000 samples, GroupKFold split)",
        training_date="2026-09-15",
        status="ACTIVE",
        metrics={
            "impact_framework_consistency_f1": 0.9695,
            "independent_predictive_validity_f1": 0.1744,
            "critical_recall": 0.9682,
            "high_recall": 0.9580,
            "robustness_retained": 0.9389
        },
        limitations="Impact-framework derived S_impact label correlation disclosed; independent non-target feature F1 reported separately."
    )
)

ModelRegistry.register(
    ModelRegistryItem(
        name="risk-prediction-gb-realworld",
        version="2.0.0-realworld",
        purpose="Predicts forward 24h disaster risk score (0-100) and level (LOW to EXTREME) on 0.25° grid cell",
        framework="Scikit-Learn (GradientBoostingClassifier)",
        dataset="NOAA GHCN + IMD Daily Weather Grids (5,000 station days, Temporal split)",
        training_date="2026-09-15",
        status="ACTIVE",
        metrics={
            "accuracy": 0.9360,
            "macro_f1": 0.9123,
            "extreme_recall": 0.9250,
            "high_recall": 0.8940,
            "robustness_retained": 0.8567
        },
        limitations="Antecedent weather observations (T-24h to T-72h); zero temporal leakage."
    )
)

ModelRegistry.register(
    ModelRegistryItem(
        name="cv-damage-classifier-realworld",
        version="2.0.0-realworld",
        purpose="Classifies building damage severity (NO_DAMAGE to DESTROYED) from disaster evidence imagery",
        framework="ResNet18 Deep Vision Backbone + RandomForest Classifier",
        dataset="xBD (xView2) Primary Satellite Imagery (2,500 image patches, GroupKFold by scene)",
        training_date="2026-09-15",
        status="ACTIVE",
        metrics={
            "raw_satellite_benchmark_f1": 0.8210,
            "accuracy": 0.8224,
            "destroyed_recall": 0.8089,
            "severe_recall": 0.7628,
            "visual_feature_proxy_f1": 1.0000,
            "robustness_retained": 0.9752
        },
        limitations="xBD satellite primary benchmark; CrisisMMD classified as auxiliary robustness dataset."
    )
)

ModelRegistry.register(
    ModelRegistryItem(
        name="resource-demand-sphere-calibrated",
        version="2.0.0-calibrated",
        purpose="Predicts required relief supply quantities anchored in UN Sphere International Standards",
        framework="Scikit-Learn (Multi-Output RandomForestRegressor)",
        dataset="UN Sphere International Standards Calibrated Baseline (2,500 records)",
        training_date="2026-09-15",
        status="ACTIVE",
        metrics={
            "mae_overall": 4.30,
            "r2_overall": 0.9078,
            "water_packs_r2": 0.998,
            "food_packets_r2": 0.995,
            "medical_kits_r2": 0.892
        },
        limitations="Standards-calibrated synthetic model; micro-level field deployment logs are absent."
    )
)
