# DIRS System Architecture Specification

## Overview
DIRS is designed as a **Modular Monolith** with a decoupled **AI/ML Layer** and a **PostGIS Spatial Database**.

```text
+-----------------------------------------------------------------------+
|                           REACT FRONTEND                              |
|   Citizen Portal | Volunteer Portal | NGO Portal | Command Center      |
|   MapLibre / Leaflet GIS | Recharts Analytics | TanStack Query        |
+-----------------------------------------------------------------------+
                                   | HTTP / REST & WebSockets
+-----------------------------------------------------------------------+
|                          FASTAPI BACKEND                              |
|   API Routers (Auth, Incidents, Shelters, Volunteers, Resources)      |
|   Core Security (JWT, bcrypt, RBAC Dependencies)                       |
|   Service Layer (Business Logic, Spatio-Temporal Filters)             |
|   WebSocket Connection Manager (Live Event Broadcasts)                |
+-----------------------------------------------------------------------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
+---------------------------------+        +---------------------------------+
|      POSTGRESQL + POSTGIS       |        |          REDIS CACHE            |
| Spatial Tables, Spatial Indexes |        | Pub/Sub, Rate Limits, Cache     |
+---------------------------------+        +---------------------------------+
         |                                                   |
+-----------------------------------------------------------------------+
|                           AI / ML LAYER                               |
|   Disaster Risk Engine (XGBoost/scikit-learn)                         |
|   Explainable Severity & Priority Scoring Matrix                      |
|   Computer Vision Damage Classifier (OpenCV/PyTorch)                  |
|   Disaster-Aware Route Optimizer (A* / Dijkstra)                      |
|   Smart Shelter & Resource Allocator (MCDA / SciPy Assignment)        |
|   Spatio-temporal Duplicate Clustering (DBSCAN / Distance Matrix)     |
|   Grounded Emergency Safety RAG Assistant                             |
+-----------------------------------------------------------------------+
```

## Modular Monolith Design Principles
1. **Clear Domain Boundaries:** Routers only validate HTTP inputs and invoke domain services.
2. **Service Layer:** Business rules, scoring formulas, and database operations reside strictly in domain services.
3. **Async PostGIS ORM:** Database operations use SQLAlchemy with PostGIS spatial geometry mapping (`Geometry('POINT', srid=4326)`).
4. **Decoupled AI Engines:** AI models operate as pure Python services called directly by backend services or scheduled background tasks.
5. **Realtime Pub/Sub:** FastAPI WebSockets broadcast incident alerts and status updates using Redis pub/sub channels.
