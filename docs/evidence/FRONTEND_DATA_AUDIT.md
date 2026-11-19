# DIRS — Frontend Data Audit & Anti-Mock Inventory

Last Updated: 2026-09-10

This document contains a forensic line-by-line audit of all React components in `frontend/src/` to classify operational data sources as **Real API Integration**, **UI Local State / Simulation**, or **Static Mock**.

---

## Data Audit Summary Table

| Page / Component | Feature / UI Element | Source of Data | Real API / Static / Mock | Status & Notes |
| ---------------- | -------------------- | -------------- | ------------------------ | -------------- |
| `Login.tsx` | User Login & Authentication | `POST /auth/login` & `GET /auth/me` | **Real API** | VERIFIED: Authenticates credentials, stores JWT in localStorage, populates user context. |
| `Register.tsx` | User Registration | `POST /auth/register` | **Real API** | VERIFIED: Registers Citizen, Volunteer, NGO, or Govt accounts with hashed passwords. |
| `CitizenDashboard.tsx` | Active Emergency Incidents | `GET /incidents` | **Real API** | VERIFIED: Renders active disaster reports from backend DB. |
| `CitizenDashboard.tsx` | Emergency Geofenced Alerts | `GET /alerts` | **Real API** | VERIFIED: Fetches live emergency alerts from backend alerts router. |
| `CitizenDashboard.tsx` | SOS Distress Signal Button | `POST /incidents/sos` | **Real API** | VERIFIED: Captures browser HTML5 geolocation and triggers critical backend incident. |
| `CitizenDashboard.tsx` | Quick Report Incident Modal | `POST /incidents` | **Real API** | VERIFIED: Submits incident title, type, location, description to backend. |
| `CitizenDashboard.tsx` | Emergency Safety Assistant Chat | Local React `useState` & `setTimeout` | **Local UI Simulation** | PARTIALLY VERIFIED: Keyword-matching safety response bot (Phase 3 Grounded RAG integration target). |
| `ReportIncident.tsx` | Multi-Step Reporting Wizard | `POST /incidents` | **Real API** | VERIFIED: Captures 7 form fields, GPS coordinates, and victim statistics into database. |
| `ShelterFinder.tsx` | Spatial Shelter Recommendations | `GET /shelters/nearby` | **Real API** | VERIFIED: PostGIS multi-criteria spatial query returns nearby shelters with suitability scores. |
| `CommandCenter.tsx` | Executive Situation KPIs | `GET /analytics/summary` | **Real API** | VERIFIED: Computes 7 live system KPIs directly from PostgreSQL database counts. |
| `CommandCenter.tsx` | Command Map & Queue | `GET /incidents` & `GET /shelters` | **Real API** | VERIFIED: Displays verified/unverified incidents and active shelters on Leaflet GIS map. |
| `CommandCenter.tsx` | Live Activity Feed | WebSocket `/ws/feed` | **Real API** | VERIFIED: Listens on WebSocket channel and appends real-time events. |
| `CommandCenter.tsx` | Incident Verification Action | `PUT /incidents/{id}/verify` | **Real API (Fixed)** | VERIFIED: Wired to backend verification endpoint to update incident status. |
| `VolunteerDashboard.tsx` | Volunteer Profile & Verification | `GET /volunteers/me` | **Real API** | VERIFIED: Retrieves logged-in volunteer profile, skills, and verification status. |
| `VolunteerDashboard.tsx` | Rescue Task Pipeline | `GET /volunteers/me` & `PATCH /volunteers/tasks/{id}/status` | **Real API (Fixed)** | VERIFIED: Fetches assigned tasks and transitions state (`ACCEPTED` -> `COMPLETED`). |
| `NGODashboard.tsx` | Inventory Stock List | `GET /resources` | **Real API** | VERIFIED: Fetches NGO and Government inventory stock from PostgreSQL database. |
| `NGODashboard.tsx` | Add Inventory Form | `POST /resources` | **Real API** | VERIFIED: Inserts new resource stock records into database. |
| `NGODashboard.tsx` | Stock Dispatch Action | `POST /resources/{id}/dispatch` | **Real API (Fixed)** | VERIFIED: Executes transactional stock reservation and dispatch to incident zones. |

---

## Detailed Findings

1. **Anti-Mock Score:** **94.4% Real API Integration**.
2. **Identified & Fixed Gaps:**
   - `CommandCenter.tsx`: Verification button route aligned to `PUT /incidents/{id}/verify` backend endpoint.
   - `VolunteerDashboard.tsx`: Task pipeline updated from static local `useState` to real backend tasks from `GET /volunteers/me` and `PATCH /volunteers/tasks/{id}/status`.
   - `NGODashboard.tsx`: "Dispatch Stock" button wired to transactional backend endpoint `POST /resources/{id}/dispatch`.
3. **Conceptual / Local Features:**
   - Safety Chat Bot in `CitizenDashboard.tsx` operates locally via regex keyword matching pending Phase 3 Grounded RAG integration.
