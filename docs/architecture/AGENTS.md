# AGENTS.md — DIRS Development & Collaboration Rules

## Project Mission
DIRS (Disaster Intelligence and Response System) is an AI-powered disaster management decision-support platform connecting Citizens, Volunteers, NGOs, and Government Command Administrators across Pre-Disaster, During-Disaster, and Post-Disaster lifecycle stages.

## Team Roles & Ownership
- **SHUBH**: Frontend, UI/UX, Citizen Portal, Volunteer UI, Map Visualizations, Dashboards.
- **ARITRA**: Backend, Database, PostGIS, Authentication, APIs, WebSockets, Security.
- **HARSHIT**: AI/ML, Risk Prediction, Severity Engine, Computer Vision, Priority Matrix, GIS Intelligence, Optimization, RAG Assistant.
- **KAMAL**: Government Dashboard, NGO Portal, Resource Management, Admin Workflows, DevOps, Docker, CI/CD, Testing.

## Critical Engineering Guidelines
1. **Real Implementation over Fake Demos:** Never mock AI numbers or fake responses without clearly labeling them as simulation/demo modes.
2. **Never Swallow Errors:** Log full tracebacks and raise explicit HTTP/Python exceptions.
3. **No Unnecessary Microservices:** Maintain a clean modular monolith architecture with separated AI/GIS service modules.
4. **PostGIS First:** Use proper PostGIS spatial geometry data types (`GEOMETRY(Point, 4326)`) and spatial indexing rather than flat lat/lng math where spatial queries are required.
5. **Role Security:** Enforce server-side RBAC on every protected route (`CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`).
6. **No Secrets in Repo:** Always use environment variables loaded from `.env`.
7. **Quality Gates:** Verify backend unit tests, frontend builds, database migrations, and API health before declaring features complete.
