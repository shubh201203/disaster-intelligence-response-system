# DIRS GIS & Spatial Analytics Specification

## Overview
Geospatial intelligence is core to DIRS. The GIS subsystem combines PostGIS backend spatial query primitives (`ST_DWithin`, `ST_Distance`) with frontend interactive map rendering using **MapLibre GL JS** or **Leaflet**.

## GIS Layers

1. **Live Incident Layer:** Color-coded severity markers (Critical = Red, High = Orange, Medium = Yellow, Low = Blue) with real-time status badges.
2. **Risk Zone Heatmap:** Density maps depicting disaster risk prediction zones.
3. **Volunteer Location Layer:** Real-time coordinates of available vs active rescue personnel.
4. **Shelter Layer:** Capacity pie indicators and medical/food/water facility toggles.
5. **Resource Distribution Layer:** NGO and Government supply centers.
6. **Road Blockages & Hazard Layer:** Active road obstructions avoided during rescue routing.

## Disaster-Aware Routing (`ai/routing_engine.py`)
- Algorithm: A* / Dijkstra shortest-path pathfinding across open road graph edges while setting infinite edge weight penalties on blocked road segments and high-hazard flood zones.
- Output: Route GeoJSON, distance (km), estimated time of arrival (ETA), and avoided hazard list.
