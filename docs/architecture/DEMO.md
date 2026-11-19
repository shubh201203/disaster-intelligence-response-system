# DIRS — Phase 3A + Phase 3B + Phase 3C Disaster Intelligence Demo Specification

Last Updated: 2026-09-15 (Phase 3C Approved & Fully Verified)

This document describes the reproducible 18-step scenario script [`scripts/run_demo_scenario.py`](file:///C:/Users/shubh/Downloads/DIRS/scripts/run_demo_scenario.py) demonstrating the complete DIRS disaster response lifecycle, AI intelligence, and Grounded RAG decision copilot capabilities.

---

## 1. Demo Scenario Overview

* **Disaster Event:** Category 4 Cyclone "Vardah" Landfall & Secondary Riverfront Flash Flooding
* **Script Location:** [`scripts/run_demo_scenario.py`](file:///C:/Users/shubh/Downloads/DIRS/scripts/run_demo_scenario.py)
* **Execution Command:** `python scripts/run_demo_scenario.py`

---

## 2. 18-Step Execution Flow

1. **Database Reset & Role Accounts:** Seeds `GOVT`, `CITIZEN`, `VOLUNTEER`, `NGO` accounts, shelters, and relief inventory.
2. **Emergency Alert Broadcast:** Admin issues Cyclone & Evacuation Alert.
3. **Citizen Distress Submission:** Citizen Rahul submits SOS incident report for 8 trapped citizens.
4. **AI Severity Classification:** Severity engine evaluates report (`MEDIUM`, 87% confidence) with explainable factors.
5. **AI Priority Scoring:** Priority engine computes normalized score (34.4 / 100).
6. **AI Duplicate Detection:** Spatio-temporal detector flags duplicate report (84.5% similarity).
7. **Government Verification:** Government Officer approves AI recommendation and verifies incident.
8. **Volunteer Dispatch:** Matching engine assigns nearby certified responder Priya.
9. **Rescue Task Lifecycle:** Priya transitions task (`ACCEPTED` -> `EN_ROUTE` -> `ARRIVED` -> `RESCUE_STARTED` -> `COMPLETED`).
10. **Incident Resolution:** System auto-resolves incident and logs audit trail.
11. **Phase 3B Computer Vision:** CV engine analyzes evidence photo (`LOW_DAMAGE`, 4x4 Saliency Grid).
12. **Phase 3B Risk Prediction:** Meteorological model predicts risk score (74.2, `EXTREME`) with 6 contributing factors.
13. **Phase 3B Resource Demand:** Multi-output regressor forecasts resource needs and detects stock shortages.
14. **Phase 3B Government AI Override:** Government Officer overrides prediction level with audit logging.
15. **Phase 3C Knowledge Seeding:** Vector index seeds NDMA, FEMA, and WHO authoritative guidelines.
16. **Phase 3C Grounded RAG Query:** RAG Copilot retrieves grounded situation summary, verified facts, and citations.
17. **Phase 3C Decision Recommendations:** Recommendation Engine generates structured action options for evacuation, triage, and shelters.
18. **Phase 3C Government Decision Approval:** Government Officer approves (`ACCEPTED`) recommendation with immutable audit trail.
