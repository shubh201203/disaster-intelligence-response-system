# DIRS Phase 5A — Optimization Layer Real vs Synthetic Data Strategy

## Executive Summary

To validate the Phase 5 Optimization Layer with scientific rigor without introducing unverified live dependencies during testing, a hybrid data strategy is defined. 

This document delineates the boundary between **operational production data** (actual PostGIS incident coordinates, resource inventories, shelter occupancies) and **calibrated synthetic baseline data** (road network graph edges, vehicle fleet specifications, and dynamic disaster disruption events).

---

## 1. Operational Data Source Boundary Matrix

| Optimization Component | Data Type | Primary Source | Production Ingestion Mechanism | Synthetic Fallback Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Incidents & Demand** | Operational Real | `incidents` table + Phase 3A Predictor | DB queries (`Incident.geom`, `severity_level`) | Seeded Chennai Cyclone Vardah incident set |
| **Depots & Inventory** | Operational Real | `resources` table | DB queries (`Resource.location_lat`, `available_quantity`) | Calibrated regional distribution centers |
| **Shelters & Occupancy** | Operational Real | `shelters` table | DB queries (`Shelter.total_capacity`, `current_occupancy`) | Standard disaster relief shelters |
| **Road Network Graph** | Hybrid Real/Synthetic | PostGIS + OpenStreetMap / `NetworkX` | `RoadBlockage` table + OSMnx edge distance query | Grid graph with GeoJSON road geometries |
| **Vehicle Fleet** | Calibrated Synthetic | Phase 5 In-Memory Vehicle Generator | DB `Vehicle` table (to be created in Phase 5B) | Standardized transport fleet (Trucks, Ambulances, Boats) |
| **Volunteer Skills** | Operational Real | `volunteer_profiles` table | Structured JSON skills parsing | Skill-categorized volunteer profiles |

---

## 2. Road Network Graph & Travel Matrix Strategy

```
┌───────────────────────────────────────────────────────────┐
│ PostGIS WGS84 Geometries (Incidents, Depots, Blockages)   │
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ Graph Ingestion Engine                                    │
│ 1. Primary: NetworkX Graph constructed from GeoJSON edges │
│ 2. Secondary: Dynamic Weight Adjuster                     │
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ Dynamic Blockage & Penalty Application                    │
│ - Impassable Blockage: edge_weight = ∞ (Edge Removed)     │
│ - Debris / De-flooding: edge_weight = base_weight * 3.5  │
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ Distance & Time Matrix Generation                        │
│ - nxn All-Pairs Shortest Path (Dijkstra / SciPy)          │
│ - Matrix fed into OR-Tools Routing Model                  │
└───────────────────────────────────────────────────────────┘
```

### Graph Technical Specifications
- **Node Scale**: Up to 500 network nodes representing road intersections, depots, shelters, and incidents.
- **Edge Weight Calculation**: Haversine / Vincenty distance ($km$) converted to travel time ($minutes$) assuming baseline travel speed of $45 \text{ km/h}$ for trucks, $60 \text{ km/h}$ for ambulances, and $15 \text{ km/h}$ for boats in flooded sectors.
- **Dynamic Weight Adjuster**: Intersects PostGIS `RoadBlockage` point buffers ($100m$ radius) with graph edges. Impassable blockages mark edge traversal as forbidden ($x_{m,n,v} = 0$).

---

## 3. Standardized Phase 5 Benchmark Dataset Scale

To ensure consistent performance testing across Phase 5 development, all benchmark scripts will execute against the **DIRS-50 Standard Evaluation Benchmark Scale**:

- **Active Incidents ($N$)**: 50 geographically dispersed disaster incidents.
- **Supply Depots ($M$)**: 10 major warehouses and regional relief stockpiles.
- **Vehicle Fleet ($K_v$)**: 25 emergency vehicles (12 Cargo Trucks, 8 Ambulances, 5 Rescue Boats).
- **Shelters ($K$)**: 15 evacuation shelters with capacity tracking.
- **Volunteers**: 100 registered volunteers with categorised medical, rescue, and logistics skill tags.
- **Dynamic Blockages**: 8 active road blockages (4 impassable, 4 delayed).
