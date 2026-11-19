# DIRS Phase 5A — Current Data Model & Database Schema Audit Report

## Executive Summary

Before formulating the Phase 5 Optimization Layer, a comprehensive audit of the existing DIRS database schemas (`backend/app/models/`) and AI service prediction interfaces was conducted. 

The audit evaluated 24 required optimization inputs across 4 status classifications:
- **`EXISTS`**: Fully implemented database column or model entity.
- **`PARTIALLY_EXISTS`**: Data present in un-indexed JSON blobs or spatial geometries without dedicated optimization tables.
- **`MISSING`**: Required optimization input currently absent from backend models.
- **`DERIVED`**: Computed dynamically by Phase 3A, Phase 3B, or Phase 4 AI engines.

---

## 1. Complete Optimization Input Audit Matrix

| Optimization Input Dimension | System Status | Current Model / Location | Schema & Implementation Detail |
| :--- | :---: | :--- | :--- |
| **Incidents** | **`EXISTS`** | `Incident` (`incidents` table) | Primary entity (`id`, `title`, `disaster_type`, `status`) |
| **Incident Coordinates** | **`EXISTS`** | `Incident.latitude`, `Incident.longitude`, `Incident.geom` | PostGIS WGS84 Point geometry (`srid=4326`) |
| **Incident Severity** | **`EXISTS`** | `Incident.severity_level` | 4-tier severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) |
| **Priority Scores** | **`EXISTS`** | `Incident.priority_score`, `Incident.priority_level` | 0–100 continuous score calculated by Priority Engine |
| **Disaster Types** | **`EXISTS`** | `Incident.disaster_type` | Categorical hazard code (`FLOOD`, `CYCLONE`, `FIRE`, etc.) |
| **Affected Population** | **`EXISTS`** | `Incident.people_affected`, `vulnerable_count` | Integer counts for affected and vulnerable demographics |
| **Predicted Resource Demand** | **`DERIVED`** | `ResourceDemandPredictor` / `ai_breakdown` | 5 continuous resource metrics (`water`, `food`, `medical`, `shelter`, `personnel`) |
| **Resources** | **`EXISTS`** | `Resource` (`resources` table) | Resource entity (`id`, `category`, `resource_name`, `unit`) |
| **Resource Quantities** | **`EXISTS`** | `Resource.total_quantity`, `Resource.available_quantity` | Tracked stock quantities |
| **Resource Locations** | **`EXISTS`** | `Resource.location_lat`, `Resource.location_lng` | Storage point coordinates |
| **Warehouses / Depots** | **`PARTIALLY_EXISTS`** | `Resource` location coordinates | Resource lat/lng acts as storage node; dedicated `Depot` table missing |
| **Vehicles** | **`MISSING`** | `VolunteerProfile.vehicle_type` (String only) | No dedicated `Vehicle` model (`max_capacity_kg`, `fuel_range`, `status`) |
| **Vehicle Capacities** | **`MISSING`** | N/A | Missing vehicle volume ($m^3$) and weight ($kg$) capacity limits |
| **Shelters** | **`EXISTS`** | `Shelter` (`shelters` table) | Shelter entity (`id`, `name`, `address`, `status`) |
| **Shelter Capacity** | **`EXISTS`** | `Shelter.total_capacity` | Integer maximum bed capacity |
| **Shelter Occupancy** | **`EXISTS`** | `Shelter.current_occupancy` | Integer current evacuee count |
| **Volunteers** | **`EXISTS`** | `VolunteerProfile` (`volunteer_profiles` table) | Volunteer entity (`user_id`, `verification_status`, `is_available`) |
| **Volunteer Skills** | **`PARTIALLY_EXISTS`** | `VolunteerProfile.skills` (JSON List) | Unstructured JSON list (e.g. `["First Aid", "Water Rescue"]`) |
| **Volunteer Availability** | **`EXISTS`** | `VolunteerProfile.is_available` | Boolean availability flag |
| **Geographic Information** | **`EXISTS`** | PostGIS GeoAlchemy2 | Spatial geometries and distance functions (`ST_Distance`) |
| **Roads / Routes** | **`PARTIALLY_EXISTS`** | `RoadBlockage` (`road_blockages` table) | Blockage points exist; full road network graph edges missing |
| **Organizations** | **`EXISTS`** | `NGOProfile` (`ngo_profiles` table) | NGO organization profiles and registration IDs |
| **Government Users** | **`EXISTS`** | `User` (`role="GOVT"`) | RBAC Government Command Center users |
| **Audit Records** | **`EXISTS`** | `AuditLog` (`audit_logs` table) | Immutable audit trail (`action`, `performed_by`, `timestamp`) |

---

## 2. Key Gaps Identified for Phase 5 Implementation

1. **Vehicle Fleet & Transport Model (`MISSING`):**
   - Must introduce a lightweight `Vehicle` schema (or in-memory data model) specifying `vehicle_id`, `depot_id`, `capacity_kg`, `capacity_volume_m3`, `vehicle_type` (`TRUCK`, `AMBULANCE`, `BOAT`), and `is_available`.

2. **Road Network Graph (`PARTIALLY_EXISTS`):**
   - Must introduce an in-memory NetworkX road graph with dynamic edge weight adjustments derived from `RoadBlockage` records to support authentic shortest-path routing and multi-vehicle routing.

3. **Standardized Volunteer Skill Categories (`PARTIALLY_EXISTS`):**
   - Must standardize volunteer JSON skills into discrete operational categories (`MEDICAL`, `RESCUE`, `LOGISTICS`, `GENERAL_RELIEF`).
