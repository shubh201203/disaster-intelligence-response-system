# PHASE 5F-A — Current Data Model Audit & Schema Gap Analysis

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Classification:** RELATIONAL DATA AUDIT & SCHEMA EXTENSION SPECIFICATION (PRE-IMPLEMENTATION)  
**Date:** 2026-09-22  

---

## 1. Executive Summary

Phase 5F extends DIRS decision-support capabilities from commodity distribution and vehicle routing to human-centric disaster response:
1. **Shelter Assignment:** Evacuating displaced populations to safe, equipped, and accessible emergency shelters.
2. **Volunteer Assignment:** Dispatching verified, skilled responders to urgent incident tasks respecting travel times and workloads.

This document conducts a complete architectural audit of existing database models across Phase 4, Phase 5B, Phase 5C, Phase 5D, and Phase 5E, identifies existing fields that will be directly reused, and details schema extensions required to support shelter and volunteer optimization without disrupting frozen components.

---

## 2. Existing Schema Audit & Reuse Inventory

### 2.1 User & Role Architecture (`backend/app/models/user.py`)
- **`UserRole` Enum:**
  - `CITIZEN = "CITIZEN"`
  - `VOLUNTEER = "VOLUNTEER"`
  - `NGO = "NGO"`
  - `GOVT = "GOVT"`
  - *Audit Finding:* Directly reuses `UserRole.GOVT` for Human-In-The-Loop (HITL) approval gates. Reuses `UserRole.VOLUNTEER` for responder candidate pools.
- **`User` Model:**
  - `id`: UUID string primary key.
  - `full_name`, `email`, `phone`, `role`, `is_active`.
- **`VolunteerProfile` Model:**
  - Already contains Phase 5B optimization foundation:
    - `skills`: JSON array of specific capabilities (e.g., `["First Aid", "Water Rescue"]`).
    - `skill_category`: Indexed string (`MEDICAL`, `RESCUE`, `LOGISTICS`, `GENERAL`).
    - `assignment_status`: Indexed string (`UNASSIGNED`, `ASSIGNED`, `ON_MISSION`).
    - `experience_years`: Integer.
    - `vehicle_type`: String (nullable).
    - `medical_certified`: Boolean flag.
    - `verification_status`: String (`PENDING`, `VERIFIED`, `REJECTED`).
    - `is_available`: Boolean flag.
    - `current_lat`, `current_lng`: Float WGS-84 coordinates.
  - *Audit Finding:* Reusable foundation. Core responder attributes are already modeled.

### 2.2 Incident Model (`backend/app/models/incident.py`)
- **Existing Fields Reused:**
  - `id`: UUID string.
  - `title`, `disaster_type` (`FLOOD`, `CYCLONE`, `FIRE`, `LANDSLIDE`, `EARTHQUAKE`).
  - `status`: Lifecycle state (`REPORTED` through `RESOLVED`).
  - `priority_level`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
  - `priority_score`: Continuous score (0.0 to 100.0).
  - `severity_level`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
  - `latitude`, `longitude`, `geom`: PostGIS WGS-84 spatial point.
  - `people_affected`: Total displaced evacuees ($p_i$).
  - `vulnerable_count`: Accessibility-requiring evacuees ($v_i$).
  - `injuries`: Medical-care-requiring evacuees ($m_i$).
- *Demographic Partitioning:*
  To prevent double counting in the mathematical formulation:
  - $p_{i, \text{MED\_ACC}}$: Evacuees requiring both medical and accessibility care.
  - $p_{i, \text{ACC}} = v_i - p_{i, \text{MED\_ACC}}$: Accessibility only.
  - $p_{i, \text{MED}} = m_i - p_{i, \text{MED\_ACC}}$: Medical only.
  - $p_{i, \text{GEN}} = p_i - (p_{i, \text{MED\_ACC}} + p_{i, \text{ACC}} + p_{i, \text{MED}})$: General evacuees.

### 2.3 Shelter Model (`backend/app/models/shelter.py`)
- **Existing Fields Reused:**
  - `id`: UUID string.
  - `name`, `address`: Descriptive location.
  - `total_capacity`: Maximum capacity (integer).
  - `current_occupancy`: Currently occupied slots (integer).
  - `latitude`, `longitude`, `geom`: Location point.
  - `has_medical`: Boolean flag for medical aid station ($M_s$).
  - `has_food`: Boolean flag for emergency rations.
  - `has_water`: Boolean flag for clean potable water.
  - `disaster_risk_level`: String (`LOW`, `MEDIUM`, `HIGH`).
  - `status`: Operational state (`OPEN`, `FULL`, `CLOSED`).
- *Audit Finding:* Core physical capacity and occupancy tracking are in place. The effective remaining capacity is:
  $$C_s = \begin{cases} \max(0, \text{total\_capacity} - \text{current\_occupancy}) & \text{if } \text{status} = \text{"OPEN"} \\ 0 & \text{if } \text{status} \in \{\text{"FULL"}, \text{"CLOSED"}\} \end{cases}$$

### 2.4 Optimization & Audit Foundation (`backend/app/models/optimization.py`)
- **`OptimizationRun`:**
  - `id`, `status` (`PROPOSED`, `APPROVED`, `REJECTED`, `MODIFIED`), `run_timestamp`, `requesting_user_id`.
  - Metadata payloads: `objective_config_json`, `input_snapshot_json`, `solver_metadata_json`.
  - Feasibility metrics: `runtime_ms`, `optimality_gap`, `feasibility_status` (`FEASIBLE`, `PARTIALLY_FEASIBLE`, `INFEASIBLE`).
- **`OptimizationRecommendation`:**
  - `recommendation_type`: Reuses enum values `SHELTER_EVACUATION` and `VOLUNTEER_ASSIGNMENT`.
  - Foreign keys: `incident_id`, `shelter_id`, `volunteer_id`.
  - Payloads: `allocated_quantity`, `proposed_route_json`, `objective_contribution`, `explanation`.
- **`OptimizationOverrideLog` & `AuditLog`:**
  - Full immutable tracking of government officer overrides with mandatory `justification_reason`.

---

## 3. Gap Analysis & Operational Transfer Schemas

To avoid modifying frozen relational tables prior to implementation approval:

### 3.1 Shelter Operational Extensions
- `accessibility_features`: Boolean flag ($A_s$), mapping to physical accessibility.
- `power_available`: Boolean flag for generator capability.
- `sanitation_available`: Boolean flag for compliant toilet ratios.
- `disaster_compatibility`: List[str] of compatible hazard types.
- `last_verified_at`: DateTime of last site inspection.

### 3.2 Volunteer Operational Extensions
- `max_shift_hours`: Float ceiling (default: $8.0\text{ h}$).
- `max_travel_time_mins`: Float reachability window (default: $45.0\text{ min}$).
- `shift_availability`: List[str] of active operational shift IDs.

### 3.3 Incident Operational Extensions
- `required_skills`: Dict[str, int] of required responder roles ($d_{ikt}$).
