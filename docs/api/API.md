# DIRS REST & WebSocket API Specification

## Base URL
`/api/v1`

## Authentication
All protected endpoints require an `Authorization: Bearer <JWT_TOKEN>` header.

---

## Endpoint Catalog

### 1. System Health
- `GET /health`
  - Returns service status for API, PostgreSQL connection, Redis connection, and AI model readiness.

### 2. Authentication (`/auth`)
- `POST /auth/register` — Register a new user (`CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`).
- `POST /auth/login` — Login user and return OAuth2 JWT Access Token (`application/x-www-form-urlencoded`).
- `GET /auth/me` — Return current authenticated user profile.

### 3. Users (`/users`)
- `GET /users/me` — Get detailed user profile according to role.
- `PUT /users/me` — Update user profile.

### 4. Incidents (`/incidents`)
- `GET /incidents` — Query incidents (supports status, severity, disaster_type, and spatial bounds filters).
- `POST /incidents` — Report a new incident (GPS location, description, victims, injuries, optional media).
- `POST /incidents/sos` — Trigger emergency high-priority SOS distress panic signal.
- `GET /incidents/{id}` — Get detailed incident by ID.
- `PUT /incidents/{id}/verify` — [GOVT] Verify or reject an incident.
- `POST /incidents/{id}/merge` — [GOVT] Merge duplicate incident reports into a cluster.
- `GET /incidents/nearby` — Query incidents within radius (km) using PostGIS.

### 5. Shelters (`/shelters`)
- `GET /shelters` — List active shelters with capacity and occupancy.
- `GET /shelters/nearby` — Find nearest suitable shelters given GPS location and medical/occupancy filters.
- `POST /shelters` — [GOVT] Create a new emergency shelter.

### 6. Volunteers (`/volunteers`)
- `GET /volunteers` — [GOVT/NGO] Query volunteers by skills and verification status.
- `GET /volunteers/me` — Get active volunteer status and tasks.
- `POST /volunteers/{id}/verify` — [GOVT] Approve or reject volunteer application.
- `POST /volunteers/tasks/{id}/status` — Update rescue task execution status (`ASSIGNED`, `ACCEPTED`, `EN_ROUTE`, `ARRIVED`, `COMPLETED`).

### 7. Resources (`/resources`)
- `GET /resources` — List available NGO & Government relief inventory.
- `POST /resources` — Add or update resource inventory.
- `POST /resources/request` — Submit resource request for an incident.
- `POST /resources/{id}/dispatch` — Reserve and dispatch stock quantity.

### 8. Alerts (`/alerts`)
- `GET /alerts` — List active emergency alerts for user location.
- `POST /alerts` — [GOVT] Create geofenced emergency warning or evacuation alert.

### 9. Analytics (`/analytics`)
- `GET /analytics/summary` — [GOVT] Get executive situation summary (active incidents, affected victims, shelter capacity, active rescues).

### 10. AI Intelligence (`/ai`)
- `GET /ai/models` — List registered AI intelligence models and evaluation metadata.
- `POST /ai/incidents/{id}/severity` — [GOVT] Predict disaster severity class, calculate confidence score, and generate explainability factors.
- `POST /ai/incidents/{id}/priority` — [GOVT] Calculate transparent 0-100 priority score and factor breakdown.
- `POST /ai/incidents/{id}/duplicates` — [GOVT] Detect spatio-temporal-text candidate duplicates with similarity evidence.
- `POST /ai/incidents/{id}/analyze` — [GOVT] Execute full AI pipeline (Severity + Priority + Duplicates).

### 11. WebSockets (`/ws`)
- `WS /ws/feed` — Real-time event subscription (`INCIDENT_CREATED`, `INCIDENT_VERIFIED`, `SOS_TRIGGERED`, `AI_SEVERITY_UPDATED`, `AI_PRIORITY_UPDATED`, `DUPLICATE_DETECTED`).
