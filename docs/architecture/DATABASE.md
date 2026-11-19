# DIRS Database Architecture & PostGIS Schema

## Overview
DIRS relies on PostgreSQL with the **PostGIS** extension enabled (`srid=4326` WGS84 projection). Spatial geometry columns (`GEOMETRY(Point, 4326)`) are used for spatial indexing, range queries, and proximity scoring.

## ER Schema Breakdown

### 1. Users & RBAC
- `users`: `id` (UUID), `email` (string, unique), `hashed_password` (string), `full_name` (string), `role` (enum: `CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`), `phone` (string), `is_active` (bool), `created_at` (timestamp).
- `citizen_profiles`: `id` (UUID), `user_id` (FK -> users.id), `emergency_contact_name` (string), `emergency_contact_phone` (string), `address` (string), `latitude` (float), `longitude` (float).
- `volunteer_profiles`: `id` (UUID), `user_id` (FK -> users.id), `skills` (JSON array), `experience_years` (int), `vehicle_type` (string), `medical_certified` (bool), `verification_status` (enum: `PENDING`, `VERIFIED`, `REJECTED`), `is_available` (bool), `current_lat` (float), `current_lng` (float).
- `ngo_profiles`: `id` (UUID), `user_id` (FK -> users.id), `org_name` (string), `registration_no` (string), `contact_person` (string), `address` (string), `verified` (bool).

### 2. Incidents & Reports
- `incidents`: `id` (UUID), `incident_code` (string, unique, e.g. `INC-2026-1001`), `title` (string), `disaster_type` (string, e.g., FLOOD, CYCLONE, FIRE, LANDSLIDE), `description` (text), `status` (enum: `REPORTED`, `AI_ANALYZED`, `PENDING_VERIFICATION`, `VERIFIED`, `PRIORITIZED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`), `priority_level` (enum: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), `priority_score` (float 0-100), `severity_level` (string), `confidence_score` (float 0-100), `latitude` (float), `longitude` (float), `geom` (Geometry(Point, 4326)), `people_affected` (int), `injuries` (int), `vulnerable_count` (int), `infrastructure_damage` (text), `created_at` (timestamp), `updated_at` (timestamp), `resolved_at` (timestamp).
- `incident_reports`: `id` (UUID), `incident_id` (FK -> incidents.id), `reporter_id` (FK -> users.id), `report_text` (text), `media_urls` (JSON array), `latitude` (float), `longitude` (float), `created_at` (timestamp).
- `incident_clusters`: `id` (UUID), `cluster_code` (string), `primary_incident_id` (FK -> incidents.id), `duplicate_count` (int), `spatial_radius_m` (float), `temporal_span_min` (int), `created_at` (timestamp).

### 3. Shelters & Resources
- `shelters`: `id` (UUID), `name` (string), `address` (string), `total_capacity` (int), `current_occupancy` (int), `latitude` (float), `longitude` (float), `geom` (Geometry(Point, 4326)), `has_medical` (bool), `has_food` (bool), `has_water` (bool), `disaster_risk_level` (string), `status` (enum: `OPEN`, `FULL`, `CLOSED`).
- `resources`: `id` (UUID), `owner_type` (enum: `NGO`, `GOVT`), `owner_id` (FK -> users.id), `category` (enum: `FOOD`, `WATER`, `MEDICINE`, `CLOTHING`, `VEHICLE`, `GENERATOR`), `resource_name` (string), `total_quantity` (int), `available_quantity` (int), `unit` (string), `location_lat` (float), `location_lng` (float).
- `resource_requests`: `id` (UUID), `incident_id` (FK -> incidents.id), `requester_id` (FK -> users.id), `category` (string), `quantity_requested` (int), `priority` (string), `status` (enum: `PENDING`, `APPROVED`, `DISPATCHED`, `FULFILLED`, `REJECTED`).

### 4. Operations & System
- `rescue_tasks`: `id` (UUID), `incident_id` (FK -> incidents.id), `assigned_type` (enum: `VOLUNTEER`, `NGO`, `GOVT_TEAM`), `assigned_id` (FK -> users.id), `status` (enum: `ASSIGNED`, `ACCEPTED`, `EN_ROUTE`, `ARRIVED`, `RESCEU_STARTED`, `COMPLETED`), `assigned_at` (timestamp), `completed_at` (timestamp).
- `road_blockages`: `id` (UUID), `title` (string), `hazard_type` (string), `latitude` (float), `longitude` (float), `geom` (Geometry(Point, 4326)), `severity` (string), `created_at` (timestamp).
- `alerts`: `id` (UUID), `title` (string), `message` (text), `alert_type` (enum: `EVACUATION`, `WARNING`, `SHELTER`, `GENERAL`), `target_zone_lat` (float), `target_zone_lng` (float), `radius_km` (float), `created_by` (FK -> users.id), `created_at` (timestamp).
- `donations`: `id` (UUID), `donor_name` (string), `donor_email` (string), `amount` (float), `currency` (string), `target_disaster` (string), `transaction_id` (string), `status` (string), `created_at` (timestamp).
- `audit_logs`: `id` (UUID), `user_id` (FK -> users.id), `action` (string), `target_entity` (string), `details` (JSON), `ip_address` (string), `timestamp` (timestamp).
- `ai_predictions`: `id` (UUID), `entity_type` (string), `entity_id` (string, indexed), `prediction_type` (string: `SEVERITY`, `PRIORITY`, `DUPLICATE`), `model_name` (string), `model_version` (string), `prediction` (string), `confidence` (float), `requires_human_review` (bool), `explanation` (JSON), `input_snapshot` (JSON), `created_at` (timestamp).

## Spatial Indexes
- `idx_incidents_geom`: GIST index on `incidents.geom`
- `idx_shelters_geom`: GIST index on `shelters.geom`
- `idx_road_blockages_geom`: GIST index on `road_blockages.geom`
