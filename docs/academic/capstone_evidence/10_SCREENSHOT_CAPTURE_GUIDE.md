# DIRS — Screenshot Capture Guide & Visual Evidence Catalog
## Visual Artifact Specification, Step-by-Step UI Staging & Presentation Figure Index

**Document Identifier:** `DIRS-CAPSTONE-EVIDENCE-10`  
**Classification:** OFFICIAL / ACADEMIC CAPSTONE EVIDENCE  
**Parent System:** Disaster Intelligence and Response System (DIRS)  
**Target Release:** DIRS v6.0 (Enterprise Hardened) / Capstone Release  
**Status:** Certified Visual Documentation Guide  

---

## 1. Visual Evidence Overview & Staging Instructions

This document provides a comprehensive staging and capture guide for all visual figures required in the final VIT-AP B.Tech Capstone Project Report and evaluation slide deck.

To capture high-resolution figures matching academic publishing standards:
1. Ensure the backend (`uvicorn app.main:app --port 8000`) and frontend (`npm run dev`) are running locally.
2. Launch a browser window at standard full-HD resolution (**1920 × 1080**) with browser zoom set to **100%**.
3. Use a system screen capture utility (e.g. Windows Snipping Tool `Win + Shift + S`) or browser full-page capture to save images as PNG.
4. Name captured figures according to the prescribed filenames in Section 2.

---

## 2. Definitive Screen Inventory & Staging Walkthrough (14 Key Figures)

```
+----------------------------------------------------------------------------------------------------+
|                                    DIRS VISUAL EVIDENCE INDEX                                      |
+----+---------------------------------------------+-----------------------------+------------------+
| #  | Figure Title                                | Route & Role                | Target Filename  |
+----+---------------------------------------------+-----------------------------+------------------+
| 01 | Unified Role-Based Authentication Gateway   | `/login` (Public)           | `fig_01_login`   |
| 02 | Citizen Emergency Incident Intake Form      | `/citizen` (CITIZEN)        | `fig_02_cit_rep` |
| 03 | Citizen Operations Console & Recovery Card  | `/citizen` (CITIZEN)        | `fig_03_cit_dash`|
| 04 | Volunteer Mission Queue & Field Inspection  | `/volunteer` (VOLUNTEER)    | `fig_04_vol_insp`|
| 05 | NGO Multi-Agency Inventory Scoping Console  | `/ngo` (NGO)                | `fig_05_ngo_scop`|
| 06 | Command Center Emergency Incident Triage    | `/admin` (GOVT/ADMIN)       | `fig_06_cmd_tri` |
| 07 | Engineering Damage Assessment Gate Modal    | `/admin` (GOVT/ADMIN)       | `fig_07_eng_gate`|
| 08 | Infrastructure Precedence (CPM-PL) Network  | `/admin` (GOVT/ADMIN)       | `fig_08_cpm_dag` |
| 09 | Dry-Run Topological Cycle Rejection Drawer  | `/admin` (GOVT/ADMIN)       | `fig_09_dag_cycl`|
| 10 | Community Recovery Simulation Workbench     | `/admin/simulation` (ADMIN) | `fig_10_sim_wrk` |
| 11 | Recovery Optimization Scenario Configuration| `/admin/recovery-opt` (ADM) | `fig_11_opt_cfg` |
| 12 | Periodic Gantt Schedule & Dual Solvency     | `/admin/recovery-opt` (ADM) | `fig_12_opt_gnt` |
| 13 | 4-Tier Infeasibility Diagnostics Core Modal | `/admin/recovery-opt` (ADM) | `fig_13_inf_diag`|
| 14 | Automated Test Pyramid Terminal Execution   | Terminal (PowerShell)       | `fig_14_tst_term`|
+----+---------------------------------------------+-----------------------------+------------------+
```

---

### Figure 01: Unified Role-Based Authentication Gateway
* **Target File:** `fig_01_unified_login_portal.png`
* **Route & Access:** `/login` | Public Unauthenticated
* **Staging Steps:**
  1. Open a clean browser window to `http://localhost:5173/login`.
  2. Ensure the login card is centered with username/email and password fields visible.
* **Key Highlights to Annotate:**
  - Clean branded hero banner: "Disaster Intelligence & Response System".
  - Secure credential form with validation indicators.
  - Role-agnostic authentication gateway mapping tokens to role-specific layouts.
* **Academic Purpose:** Demonstrates secure perimeter access control and single entry-point role resolution.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 02: Citizen Emergency Incident Intake Form & Offline Staging
* **Target File:** `fig_02_citizen_incident_intake.png`
* **Route & Access:** `/citizen` (or modal) | Role: `CITIZEN` (`citizen@dirs.org`)
* **Staging Steps:**
  1. Log in as `citizen@dirs.org`.
  2. Click **Report Incident** in the navigation header.
  3. Pre-fill data: Title "Flash Flooding near Adyar Riverfront", Type `FLOOD`, Severity `4 - High`, Casualties `2`.
  4. Hover over **Save Local Draft**.
* **Key Highlights to Annotate:**
  - Structured triage fields (Disaster Category, Severity Level 1–5, Victim Count, Location GPS).
  - Prominent dual submission actions: "Submit Incident" vs. "Save Local Draft".
  - Form validation indicators preventing incomplete submissions.
* **Academic Purpose:** Illustrates intuitive crowd-sourced emergency reporting under extreme civilian stress.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 03: Citizen Operations Console, Recovery Status & Sync Drawer
* **Target File:** `fig_03_citizen_console_and_sync_drawer.png`
* **Route & Access:** `/citizen` | Role: `CITIZEN` (`citizen@dirs.org`)
* **Staging Steps:**
  1. Click **Save Local Draft** on the report form.
  2. Notice the green banner: *"1 local draft ready for synchronization"*.
  3. Click **Manage Queue** to open the `DraftSyncManager` drawer on the right side.
* **Key Highlights to Annotate:**
  - **Municipal Recovery Status Card:** Visual display of Ward 172 baseline recovery progress.
  - **Offline Resilience Banner:** Status indicator of pending un-synchronized drafts.
  - **Draft Synchronization Manager Drawer:** Shows encrypted draft UUID, timestamp, payload preview, and single-click "Sync Now" trigger.
* **Academic Purpose:** Validates offline-first client architecture and encrypted local queue transparency.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 04: Volunteer Mission Queue & Field Inspection Intake
* **Target File:** `fig_04_volunteer_field_inspection.png`
* **Route & Access:** `/volunteer` | Role: `VOLUNTEER` (`volunteer@dirs.org`)
* **Staging Steps:**
  1. Log in as `volunteer@dirs.org`.
  2. Switch to the **Field Damage Inspection** tab.
  3. Populate inspection fields: Facility "Adyar Primary Health Centre Substation", Sector `HEALTH`, Damage `MODERATE`, Confidence `85%`.
* **Key Highlights to Annotate:**
  - Dual operational tabs: "Assigned Missions" vs. "Field Damage Inspection".
  - Standardized damage categorization (MINIMAL, MODERATE, SEVERE, CATASTROPHIC).
  - Assessor confidence scoring slider reflecting on-ground data fidelity.
* **Academic Purpose:** Demonstrates field responder empowerment and structured damage data collection.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 05: NGO Multi-Agency Inventory Scoping Console
* **Target File:** `fig_05_ngo_inventory_scoping.png`
* **Route & Access:** `/ngo` | Role: `NGO` (`ngo@dirs.org`)
* **Staging Steps:**
  1. Log in as `ngo@dirs.org`.
  2. Toggle the inventory scope switch between **All Hubs** and **My Org Only**.
  3. Display the relief demands feed from active evacuation shelters.
* **Key Highlights to Annotate:**
  - **Inventory Scope Toggle:** Clear distinction between multi-agency situational supply vs. organization depot stock.
  - **Relief Demands Feed:** Real-time commodity shortages reported by evacuation shelters.
  - **Governance Clarification:** Legal and institutional boundary notice clarifying NGO purview.
* **Academic Purpose:** Highlights multi-stakeholder supply chain transparency without jurisdictional friction.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 06: Command Center Emergency Incident Triage & Live Operations
* **Target File:** `fig_06_command_center_triage.png`
* **Route & Access:** `/admin` | Role: `GOVT` / `ADMIN` (`admin@dirs.gov`)
* **Staging Steps:**
  1. Log in as `admin@dirs.gov`.
  2. Ensure Tab 1: **Live Emergency Operations** is active.
  3. Display incoming incidents table and spatial overview.
* **Key Highlights to Annotate:**
  - High-density operational data grid with severity color tags (Red for Critical, Orange for High).
  - Status progression buttons (`VERIFY`, `DISPATCH`, `RESOLVE`).
  - Cross-ward aggregate summary cards (Total Incidents, Active Shelters, Dispatched Units).
* **Academic Purpose:** Demonstrates executive situational awareness and rapid multi-incident triage capability.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 07: Engineering Damage Assessment Certification Gate Modal
* **Target File:** `fig_07_engineering_certification_gate.png`
* **Route & Access:** `/admin` | Role: `GOVT` / `ADMIN` (`admin@dirs.gov`)
* **Staging Steps:**
  1. Select Tab 3: **Field Inspections Verification**.
  2. Click **Certify** on a pending volunteer assessment.
  3. The **Engineering Assessment Certification Gate** modal appears.
* **Key Highlights to Annotate:**
  - Mandatory professional certification boundary: Prevents unverified crowd data from corrupting civil planning.
  - Side-by-side comparison of volunteer observation vs. certified engineering classification.
  - Mandatory engineering audit rationale text field.
* **Academic Purpose:** Proves institutional data governance, audit compliance, and authoritative data verification.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 08: Infrastructure Precedence Network (CPM-PL) Graph Visualizer
* **Target File:** `fig_08_infrastructure_precedence_dag.png`
* **Route & Access:** `/admin` | Role: `GOVT` / `ADMIN` (`admin@dirs.gov`)
* **Staging Steps:**
  1. Select Tab 2: **Infrastructure Precedence (CPM-PL)**.
  2. Allow the interactive topological network to render fully.
  3. Click node `P03` to expand the right-hand **Project Inspector Drawer**.
* **Key Highlights to Annotate:**
  - Interactive SVG Directed Acyclic Graph (DAG) with sector-coded nodes.
  - **Critical Path Highlighting:** Distinct glowing crimson borders tracing the bottleneck sequence ($P01 \to P03 \to P06$).
  - **Project Inspector Drawer:** Displays exact mathematical metrics: Early Start ($ES$), Late Finish ($LF$), and Total Float ($TF = 0$).
* **Academic Purpose:** Showcases advanced graph theory and critical chain project management applied to disaster recovery.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 09: Dry-Run Topological Cycle Rejection Drawer
* **Target File:** `fig_09_dry_run_cycle_rejection.png`
* **Route & Access:** `/admin` | Role: `GOVT` / `ADMIN` (`admin@dirs.gov`)
* **Staging Steps:**
  1. In the Precedence tab, click **Validate Dependency Link**.
  2. Input an illegal backward edge (Source: `P06`, Target: `P01`).
  3. Click **Run Dry-Run Validation**.
* **Key Highlights to Annotate:**
  - Red circular dependency rejection alert banner.
  - Precise cyclic path trace: `P01 -> P03 -> P06 -> P01`.
  - Explanatory message confirming the database was not modified.
* **Academic Purpose:** Proves algorithmic guardrails preventing catastrophic deadlock in project scheduling.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 10: Community Recovery Monitoring & What-If Simulation Workbench
* **Target File:** `fig_10_community_simulation_workbench.png`
* **Route & Access:** `/admin/simulation` | Role: `ADMIN` (`admin@dirs.gov`)
* **Staging Steps:**
  1. Navigate to `/admin/simulation`.
  2. Display the **Municipal Recovery Summary** cards.
  3. Adjust the forward simulation sliders (Budget Multiplier `1.25x`, Priority Sector `POWER`) and trigger execution.
* **Key Highlights to Annotate:**
  - Multi-sector recovery index radar / line charts across Power, Water, Health, and Transport.
  - Vulnerability rescoring panel showing dynamic $\phi$ metric updates with confidence decay.
  - Projected forward recovery trajectory curves comparing baseline vs. accelerated investment.
* **Academic Purpose:** Illustrates quantitative policy simulation and dynamic community resilience tracking.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 11: Recovery Optimization Scenario Configuration Console
* **Target File:** `fig_11_optimization_scenario_config.png`
* **Route & Access:** `/admin/recovery-optimization` | Role: `ADMIN` (`admin@dirs.gov`)
* **Staging Steps:**
  1. Navigate to `/admin/recovery-optimization`.
  2. Inspect the scenario parameter cards: Horizon ($T=12$), Total Budget (₹85,00,000), Machinery CCU Bounds (8 units).
  3. Display candidate civil reconstruction project checklist.
* **Key Highlights to Annotate:**
  - Clear parameter configuration inputs with numeric constraints.
  - Candidate project selector displaying sector, duration, INR cost, and CCU demand per project.
  - Prominent "Evaluate Optimal Portfolio Schedule" dispatch button with human-in-the-loop warning.
* **Academic Purpose:** Demonstrates disciplined operational research formulation interfaces.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 12: Periodic Gantt Schedule & Dual-Ledger Solvency Matrix
* **Target File:** `fig_12_gantt_schedule_and_dual_solvency.png`
* **Route & Access:** `/admin/recovery-optimization` | Role: `ADMIN` (`admin@dirs.gov`)
* **Staging Steps:**
  1. Execute the optimization solver for Scenario 1 (₹85L, 12 periods).
  2. Display the resulting **Gantt Chart** and scroll down to the **Dual-Ledger Solvency Matrix**.
* **Key Highlights to Annotate:**
  - 1-based periodic Gantt timeline showing exact start and finish spans for all selected projects.
  - Green `OPTIMAL / FEASIBLE` solver status badge with execution duration (e.g. 1.4s).
  - Dual-Ledger Solvency Panel: Independent periodic CCU demand vs. cumulative financial burn against statutory budget ceiling.
* **Academic Purpose:** Validates the core mathematical CP-SAT scheduling engine and financial/equipment dual solvency.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 13: 4-Tier Infeasibility Diagnostics Core Modal
* **Target File:** `fig_13_infeasibility_diagnostics_modal.png`
* **Route & Access:** `/admin/recovery-optimization` | Role: `ADMIN` (`admin@dirs.gov`)
* **Staging Steps:**
  1. Modify scenario parameters: Budget ₹15,00,000, Horizon 4 periods.
  2. Click **Evaluate Optimal Portfolio Schedule** and confirm.
  3. The **Infeasibility Diagnostics Modal** automatically opens upon solver return.
* **Key Highlights to Annotate:**
  - Prominent red status banner: `INFEASIBLE — Mathematical Conflict Detected`.
  - Structured 4-tier relaxation hierarchy:
    - *Tier 1:* Horizon extension recommendation (+5 periods).
    - *Tier 2:* Capital injection recommendation (+₹32,00,000).
    - *Tier 3:* CCU resource augmentation.
    - *Tier 4:* Soft prerequisite relaxations.
* **Academic Purpose:** Demonstrates state-of-the-art diagnostic explainability in prescriptive optimization systems.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

### Figure 14: Automated Test Pyramid Terminal Execution Summary
* **Target File:** `fig_14_automated_test_pyramid_terminal.png`
* **Route & Access:** Host Terminal / PowerShell Console
* **Staging Steps:**
  1. Open PowerShell and run: `python -m pytest tests/backend/ -q`.
  2. Capture the terminal output demonstrating **656 passed in 58.03s, Exit Code: 0**.
* **Key Highlights to Annotate:**
  - Clean green terminal output showing 656 passing backend tests.
  - Sub-minute execution time proving high developer feedback velocity.
  - Zero failed tests, zero syntax warnings, and zero unhandled exceptions.
* **Academic Purpose:** Serves as empirical evidence of exhaustive automated verification and code stability.
* **Implementation Status:** **IMPLEMENTED & VERIFIED**

---

## 3. Formatting Guidelines for Report & Presentation

When inserting these figures into the Capstone Final Report:
- **Captions:** Use formal academic captions: *"Figure X.Y: Interface title and architectural significance"*.
- **Callout Arrows:** Use semi-transparent crimson callout boxes or numbered circles corresponding to text descriptions.
- **Resolution:** Maintain at least 300 DPI for print deliverables and 1080p for presentation slides.
