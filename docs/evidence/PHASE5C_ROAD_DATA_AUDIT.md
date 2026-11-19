# DIRS Phase 5C — Road Network Data Audit Report

## Executive Summary

Before implementing the Phase 5C Graph Engine, a comprehensive audit of existing road network data within the DIRS database (`backend/app/models/`) and spatial services (`backend/app/services/gis_service.py`) was conducted.

The audit evaluated 8 road/network data dimensions to establish an empirical data baseline for graph construction:

- **`EXISTS`**: Fully implemented database column or spatial entity.
- **`PARTIALLY_EXISTS`**: Data present as point coordinates or spatial geometries without full network edge connectivity tables.
- **`MISSING`**: Required graph data currently absent from production database tables.
- **`DERIVED`**: Computed dynamically via Haversine distance, speed models, or spatial PostGIS functions.

---

## 1. Complete Road Data Audit Matrix

| Network Data Dimension | Status | Current Model / Location | Technical Details & Boundary Specification |
| :--- | :---: | :--- | :--- |
| **Road Nodes (Intersections)** | **`PARTIALLY_EXISTS`** | `Incident.geom`, `Shelter.geom`, `Resource.location_lat/lng` | Demands, depots, and shelters act as network graph nodes; dedicated road intersection table missing. |
| **Road Edges (Segments)** | **`MISSING`** | N/A | No full road network topology edge table currently stored in production PostgreSQL DB. |
| **Geographic Coordinates** | **`EXISTS`** | `Incident`, `Shelter`, `Resource`, `RoadBlockage`, `Vehicle` | WGS84 Point coordinates (`latitude`, `longitude`) and PostGIS geometries (`SRID=4326`). |
| **Edge Distance ($km$)** | **`DERIVED`** | `Haversine` / `ST_Distance` calculation | Computed dynamically via geodesic Haversine formula between node coordinate pairs. |
| **Base Travel Speed** | **`DERIVED`** | Vehicle/Road default speed assumptions | Derived default speeds: Trucks = $45\text{ km/h}$, Ambulances = $60\text{ km/h}$, Boats = $15\text{ km/h}$, General = $50\text{ km/h}$. |
| **Edge Travel Time (mins)** | **`DERIVED`** | $\text{TravelTime} = \frac{\text{Distance}}{\text{Speed}} \times 60$ | Computed dynamically based on edge distance, base speed, and delay penalties. |
| **Road Status** | **`EXISTS`** | `Shelter.status`, `Vehicle.status` | Operational status flags (`OPEN`, `FULL`, `CLOSED`, `AVAILABLE`). |
| **Blockage Status** | **`EXISTS`** | `RoadBlockage` (`road_blockages` table) | Ingested from Phase 5B `RoadBlockage` model (`IMPASSABLE`, `DELAYED`, `CLEARING`, `RESOLVED`). |

---

## 2. Road Ingestion & Graph Construction Strategy

Because full OpenStreetMap (OSM) edge topologies for India are large multi-gigabyte files, DIRS Phase 5C implements a **Dual-Layer Benchmark Graph Ingestion Strategy**:

1. **Layer 1: Calibrated Regional GeoJSON Benchmark Graph (Chennai / Vardah Region)**:
   - Covers coastal Chennai and surrounding arterial corridors (East Coast Road - ECR, Old Mahabalipuram Road - OMR, Grand Southern Trunk - GST Road).
   - Ingests pre-calibrated road segment GeoJSON containing exact intersection coordinates and base speed limits.
   - Explicitly classified as: **`SYNTHETIC CALIBRATED BENCHMARK GRAPH`**.
2. **Layer 2: Dynamic Spatial Point Ingestion**:
   - Ingests active PostGIS `Incident`, `Resource` (Depot), `Shelter`, and `Vehicle` coordinates.
   - Snaps points to nearest road graph nodes using Haversine distance matching.
3. **Layer 3: Dynamic Road Blockage Penalty Adjuster**:
   - Ingests active `RoadBlockage` records from Phase 5B schema.
   - Intersects blockage coordinates with graph edges within a $100\text{m}$ buffer radius.
   - Applies state penalties: `IMPASSABLE` (edge removed / cost $\infty$), `DELAYED` (travel time + delay penalty mins).
