# DIRS Phase 6A — Forensic Current-State System Audit
## Baseline Inventory, Reusability Analysis, Data Gaps, and Architectural Boundaries

**Document ID:** `DIRS-PHASE6A-DOC-01`  
**System:** Disaster Intelligence and Response System (DIRS)  
**Audit Target:** Pre-Phase 6 Frozen Codebase (Phases 1 through 5G + Acceptance Batches 1–3)  
**Classification:** ARCHITECTURAL AUDIT / READ-ONLY  
**Author:** Principal Disaster-Management Systems Architect & Forensic Auditor  
**Date:** November 16, 2026 (Remediated Baseline)  

---

## 1. Executive Baseline Assessment

The Disaster Intelligence and Response System (DIRS) has concluded Phases 1 through 5G, achieving a verified baseline of:
- **368 / 368** passing backend automated tests across unit, integration, and regression suites.
- **19 / 19** passing dedicated acceptance tests across remediated Batches 1, 2, and 3.
- **14 / 14** verified cross-role operational lifecycle workflows spanning Citizen, Government, Volunteer, and NGO portals.
- Clean TypeScript and Vite production frontend compilation.
- Verified active runtime database environment: **PostgreSQL 18.6** with **PostGIS 3.6.2** on x86_64-windows operating with least-privilege `NOSUPERUSER` role `dirs_user`.

Phase 6 marks the architectural expansion from **acute emergency response** (hours 0 to 72) to **post-disaster recovery analytics and intelligence** (weeks 1 to 52+). This document provides a forensic audit of the repository to identify which components can be safely reused via stable interfaces without mutating frozen code, what data model gaps exist, and what technical limitations constrain recovery planning.

---

## 2. Inventory of Existing Subsystems & Code Inspection

### 2.1 Database Models and Relational Architecture

The relational architecture is implemented in SQLAlchemy 2.x declarative syntax backed by PostgreSQL 18.6 with PostGIS 3.6.2.

| Model File | Table Name | Key Schema Fields & Capabilities | Current Role in DIRS | Recovery Reusability Analysis |
| :--- | :--- | :--- | :--- | :--- |
| [`incident.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/incident.py) | `incidents` | `id`, `incident_code`, `disaster_type`, `status`, `priority_score`, `latitude`, `longitude`, `geom`, `people_affected`, `injuries`, `vulnerable_count`, `infrastructure_damage`, `required_skills`, `evacuation_demographics` | Primary disaster event entity for triage and rescue. | **High Reusability (Read-Only):** Serves as historical disaster baseline. Recovery needs assessment must anchor to specific incident centroids. Cannot be overloaded for recovery projects. |
| [`incident.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/incident.py) | `incident_reports`, `incident_media` | `report_text`, `media_urls`, `file_path`, `mime_type`, `media_type` | Citizen reports and photographic evidence. | **High Reusability:** Ground-truth photos can be linked to post-disaster damage re-inspections. |
| [`shelter.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/shelter.py) | `shelters` | `id`, `name`, `total_capacity`, `current_occupancy`, `medical_capacity`, `latitude`, `longitude`, `geom`, `status` | Acute emergency shelter housing evacuees. | **High Reusability:** Critical baseline for tracking shelter-to-home transitions and decommissioning phases. |
| [`resource.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/resource.py) | `resources` | `id`, `resource_name`, `category`, `total_quantity`, `available_quantity`, `allocated_quantity`, `location_lat`, `location_lng` | Emergency supplies (Food, Water, Medical, Hygiene, Rescue). | **Moderate Reusability:** Designed for acute consumables. Recovery requires distinct tracking of durable reconstruction materials (cement, structural steel, piping). |
| [`vehicle.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/vehicle.py) | `vehicles` | `id`, `vehicle_code`, `vehicle_type`, `capacity_kg`, `current_lat`, `current_lng`, `status` | Relief delivery and evacuation vehicles. | **Low Reusability:** Light emergency fleet vs heavy recovery equipment (excavators, dump trucks, cranes). |
| [`rescue.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/rescue.py) | `rescue_tasks` | `id`, `incident_id`, `volunteer_id`, `task_type`, `status` (`ASSIGNED`, `ACCEPTED`, `COMPLETED`), `priority` | Tactical field volunteer rescue missions. | **Moderate Reusability:** Work pattern can inspire recovery work orders, but table represents acute SAR missions. |
| [`ai.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/ai.py) | `cv_damage_assessments` | `incident_id`, `evidence_id`, `damage_class`, `confidence`, `class_probabilities`, `requires_human_review`, `is_overridden` | Single-image damage classification into 5 classes. | **Direct Reusability:** Phase 3B visual classifier can serve as Tier-1 screening for structural building damage. |
| [`ai.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/ai.py) | `risk_assessments`, `resource_demand_predictions` | `risk_score`, `risk_level`, `predictions`, `contributing_factors`, `model_version` | District risk and short-term commodity demand forecasts. | **Moderate Reusability:** Formats provide template for longitudinal recovery risk scoring. |
| [`optimization.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/optimization.py) | `optimization_runs`, `optimization_recommendations`, `optimization_override_logs` | `status`, `objective_config_json`, `runtime_ms`, `feasibility_status`, `proposed_route_json`, `justification_reason` | Human-in-the-loop dispatch and evacuation optimization. | **High Reusability Pattern:** Architectural structure for solver audits, human approval, and override tracking will be mirrored for recovery project portfolios. |
| [`simulation.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/simulation.py) | `simulation_scenarios`, `simulation_runs` | `name`, `severity_multiplier`, `delta_metrics_json`, `base_state_hash`, `result_hash`, `graph_version`, `seed` | What-if disaster simulation with strict base-state immutability. | **High Reusability:** External scenario orchestration interface directly supports recovery budget and supply shock simulations. |
| [`rag.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/rag.py) | `knowledge_documents`, `knowledge_chunks`, `rag_query_logs`, `ai_recommendations` | `title`, `source_organization`, `version_hash`, `text_content`, `embedding_vector`, `is_grounded`, `confidence` | Authoritative disaster guidelines with citation grounding. | **High Reusability:** Can ingest recovery frameworks (UNDP PDNA, World Bank, NDMA Recovery Guidelines) without schema alteration. |
| [`audit.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/audit.py) | `audit_logs` | `user_id`, `action`, `target_entity`, `details`, `ip_address`, `timestamp` | Universal immutable audit log for compliance. | **Universal Reusability:** Directly logs all recovery approvals, budget reallocations, and human overrides. |

---

### 2.2 Computer Vision Source Code Audit & Pipeline Reconciliation

A source code audit of `backend/app/ai/computer_vision/` and `backend/app/ai/models/` was conducted to reconcile documented research designs with the actual deployed runtime code:

#### A. Empirical Inspection of Code & Artifacts
1. **Actual Trained Artifact:** [`backend/app/ai/models/cv_damage_model.pkl`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/models/cv_damage_model.pkl)
   - Object Type: `sklearn.ensemble._forest.RandomForestClassifier`
   - Input Features ($D = 6$):
     - `edge_density` (Sobel gradient magnitude proxy: $\text{mean}(|dx|) + \text{mean}(|dy|)$)
     - `structural_entropy` (Shannon entropy on 16-bin grayscale histogram)
     - `color_variance` (variance across normalized RGB channels)
     - `darkness_ratio` (fraction of pixels with intensity $< 0.25$, proxy for charring/water)
     - `asymmetry_index` (mean absolute difference against horizontal mirror image, proxy for structural tilt/collapse)
     - `texture_roughness` (standard deviation of spatial gradients)
   - Output Classes: `['DESTROYED', 'LOW_DAMAGE', 'NO_DAMAGE', 'SEVERE_DAMAGE']` (with `MODERATE_DAMAGE` supported in schema mappings).
2. **Reconciliation with Phase 4 Research:** In Phase 4 research documentation (`PHASE4_FORENSIC_AUDIT.md` and `cv_model_manifest.json`), an ImageNet-pretrained `ResNet18` backbone generating 512-dim embeddings on xBD satellite benchmarks was evaluated as a deep candidate. However, to guarantee that DIRS runs reliably across standard development machines without heavy GPU or PyTorch runtime dependencies, the operational production model in `service.py` is the 6-feature Random Forest classifier.
3. **Phase 6 Role:** Serves strictly as a **read-only Tier-1 rapid screening tool** for building facades submitted by citizens or field volunteers. Certified structural assessments for roads, bridges, and utilities must rely on certified civil engineering inspection reports.

---

### 2.3 Optimization Engines (Phase 5 / 5F)
- **Current State:** Implemented in [`backend/app/ai/optimization/`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/optimization/).
- **Components:** `allocation.py` (multi-commodity acute relief LP), `routing.py` (CVRPTW), `shelter.py` (evacuee shelter assignment), `volunteer.py` (bipartite skill matching), `orchestrator.py` (integrated acute solver).
- **Forensic Assessment:** These solvers solve single-period acute relief flow. They do not support multi-period scheduling, capital expenditure budget envelopes, or precedence networks. Recovery project scheduling requires the dedicated MP-RPSP formulation.

---

### 2.4 Simulation & What-If Scenario Engine (Phase 5G)
- **Current State:** Implemented in [`backend/app/ai/simulation/scenario_engine.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/scenario_engine.py).
- **Key Architectural Strength:** Strict **base-state immutability**. Scenarios execute against deep-copied state snapshots, returning differential metrics without mutating database records.
- **Recovery Reusability:** The `DisasterScenario` structure directly provides the blueprint for Phase 6 what-if recovery simulations (budget cuts, material supply delays, secondary storm shocks).

---

## 3. Comprehensive Gap & Limitation Matrix

| Capability Dimension | Existing Operational Baseline (Phases 1–5G) | Required Post-Disaster Recovery Baseline (Phase 6) | Forensic Classification |
| :--- | :--- | :--- | :--- |
| **Damage Assessment** | Single-image 5-class building damage classification ([`cv_damage_assessments`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/ai.py#L23)). | Multi-sector infrastructure assessments (Health, Education, WASH, Power, Transport, Housing); versioning, certified engineering sign-off. | **Data & Schema Gap** |
| **Needs Assessment** | Immediate evacuation headcounts (`people_affected`, `vulnerable_count`). | Multi-sector longitudinal needs tracking; double-count prevention reconciling against official census population caps. | **Functional & Schema Gap** |
| **Prioritization** | Incident severity scoring (0–100) based on acute hazard distress. | Multi-Criteria Recovery Priority Index (MCPI) balancing life-safety, economic impact, social vulnerability, and critical facility dependencies. | **Algorithmic Gap** |
| **Resource & Funding** | Warehouse commodity dispatch (packs of food, water, hygiene kits). | Capital expenditure tracking, reconstruction material bills of quantities (cement, steel, timber), contractor workforce, budget envelopes. | **Data & Functional Gap** |
| **Infrastructure Restoration** | Static road blockage edge-status (`PASSABLE`, `IMPASSABLE`). | Directed Acyclic Graph (DAG) of restoration dependencies, Critical Path Method (CPM-PL), cycle detection, virtual node handling for disconnected networks. | **Architectural & Algorithmic Gap** |
| **Community Monitoring** | Real-time shelter occupancy (`current_occupancy`). | Longitudinal recovery indices, returnee tracking, household recovery status surveys, exponential confidence decay model. | **Schema & Service Gap** |
| **Scenario Modeling** | Disaster escalation simulation (acute incident spread, road cuts). | Multi-period recovery timeline simulations (funding shocks, supply delays, contractor capacity deficits). | **Extension Opportunity** |
| **Evaluation & Lessons** | Simple aggregate counters in [`analytics.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/routers/analytics.py) (10 metrics). | Planned vs actual recovery progress, schedule slip analysis, funding burn rate, persistent service gap identification. | **New Analytical Module** |

---

## 4. Technical Limitations & Environment Boundary Invariants

1. **Frozen Codebase Invariant:** Under no circumstances shall files in `backend/app/ai/optimization/`, `backend/app/ai/simulation/`, or existing router endpoints be modified or refactored. Phase 6 must be implemented as distinct, modular services and routers.
2. **Verified Database Environment:** Active execution runs on **PostgreSQL 18.6** with **PostGIS 3.6.2** on x86_64-windows operating with least-privilege `NOSUPERUSER` role `dirs_user`. Compatibility is verified for PostgreSQL $\ge 15.0$ and PostGIS $\ge 3.3$. Zero dependencies or drivers will be upgraded during Phase 6A remediation.
3. **No External Live Telemetry:** DIRS does not possess live IoT sensor feeds or real-time satellite radar downlinks. All recovery monitoring must consume validated field inspection records, user surveys, and administrative reports.
4. **Human Authority Primacy:** No AI model or optimization solver may approve reconstruction funding, alter civil rights, condemn private property, or issue binding recovery certifications. All outputs are strictly decision-support recommendations.

---

## 5. Current-State Audit Verdict

**AUDIT VERDICT: COMPLETE & VERIFIED.**  
The repository provides a robust, stable, and forensically validated foundation for post-disaster recovery intelligence. All candidate touchpoints for Phase 6 integration are accessible via well-defined data models and read-only interfaces.
