# DIRS Phase 6A — Final Source Verification and Provenance Audit
## Verified Authoritative References, Open Standards Catalog, and Future Integration Boundaries

**Document ID:** `DIRS-PHASE6A-DOC-14`  
**System:** Disaster Intelligence and Response System (DIRS)  
**Classification:** SOURCE VERIFICATION & DATA PROVENANCE AUDIT  
**Author:** Principal Disaster-Management Systems Architect & Forensic Auditor  
**Date:** November 16, 2026  

---

## 1. Data Integrity and Provenance Mandate

Post-disaster recovery intelligence operates under strict legal, administrative, and humanitarian accountability. Software systems that invent statistical baselines, hallucinate government funding envelopes, or conflate unverified synthetic test data with empirical disaster observations violate core engineering standards.

DIRS enforces a strict boundary between:
1. **Category A: Verified Authoritative Standards, Publications & Open Datasets** — Officially published guidelines, standards, and open spatial geometries whose methodologies, schemas, and licenses have been inspected and validated.
2. **Category B: Candidate Future Integrations** — External satellite, radar, or government enterprise feeds identified on the technology roadmap, but **not** currently integrated into the repository.

---

## 2. Category A: Verified Authoritative Sources & Standards

The following authoritative publications, international disaster management guidelines, and open geospatial standards serve as the verified foundation for DIRS Phase 6:

### 2.1 Post-Disaster Needs Assessment (PDNA) Guidelines (Volumes A & B)
- **Publishing Agencies:** United Nations Development Programme (UNDP), World Bank Global Facility for Disaster Reduction and Recovery (GFDRR), and European Union (EU).
- **Verified Publication Reference:** [GFDRR PDNA Guidelines](https://www.gfdrr.org/en/publication/post-disaster-needs-assessments-guidelines)
- **License / Access Terms:** Open Access / Public Good (Non-commercial humanitarian and governmental reuse).
- **Geographic Coverage:** Global / Multi-Hazard.
- **Update Frequency:** Decennial statutory revision with continuous sector notes.
- **Key Schemas & Methods Utilized:**
  - Multi-sector classification: Social (Housing, Health, Education), Infrastructure (WASH, Power, Transport, Telecom), Productive (Agriculture, Commerce), and Cross-cutting (Governance, Environment).
  - Mathematical definition of *Damage* (physical destruction of assets valued at replacement cost) versus *Loss* (changes in economic flows and service delivery).
  - Recovery prioritization criteria balancing basic human needs against macroeconomic restoration.
- **Known Limitations in DIRS:** PDNA provides methodological equations and survey templates; it does not provide an automated real-time API. In DIRS, PDNA rules are implemented algorithmically in `app/recovery/services/assessment_service.py`.

---

### 2.2 Sendai Framework for Disaster Risk Reduction 2015–2030 (Priority 4)
- **Publishing Agency:** United Nations Office for Disaster Risk Reduction (UNDRR).
- **Verified Publication Reference:** [UNDRR Sendai Framework](https://www.undrr.org/implementing-sendai-framework/what-sendai-framework)
- **License / Access Terms:** UN Open Access / Statutory International Agreement.
- **Geographic Coverage:** Global (187 UN Member States).
- **Key Schemas & Metrics Utilized:**
  - **Priority 4 Target:** "Enhancing disaster preparedness for effective response and to 'Build Back Better' in recovery, rehabilitation and reconstruction."
  - Target 4 Indicators: Damage to critical infrastructure (Indicator C-4) and disruptions to basic services (Indicator C-5: health, education, water, electricity).
- **Operational Role in DIRS:** Governs the evaluation metrics and lessons-learned dashboards in Subphase 6F/6G, measuring whether reconstructed assets incorporate hazard-resilient structural enhancements.

---

### 2.3 Humanitarian Data Exchange (HDX) — Common Operational Datasets (COD-AB)
- **Publishing Agency:** United Nations Office for the Coordination of Humanitarian Affairs (UN OCHA).
- **Verified Data Portal:** [Humanitarian Data Exchange](https://data.humdata.org/)
- **License / Access Terms:** Creative Commons Attribution (CC-BY 4.0).
- **Geographic Coverage:** Global by Country / Province / District / Ward.
- **Update Frequency:** Quarterly or post-boundary redrafting.
- **Key Schema Fields:**
  - `admin_level`: Administrative hierarchy (Country = 0, State = 1, District = 2, Ward/Tehsil = 3).
  - `boundary_polygon`: PostGIS Polygon / MultiPolygon spatial boundary.
  - `pcode`: Unique hierarchical identifier (e.g. `IN_TN_014`).
  - `census_population`: Verified baseline resident headcount.
- **Operational Role in DIRS:** Ingested into `recovery_needs` for spatial aggregation. Used by the Census Reconciliation Engine to cap reported affected headcounts and prevent double-counting across overlapping incident perimeters.

---

### 2.4 Schedule of Rates (SOR) for Civil Engineering Works
- **Publishing Authority:** Central Public Works Department (CPWD) & State Public Works Departments (PWD), Government of India.
- **Verified Reference:** Official CPWD Annual Schedule of Rates & Analysis of Rates.
- **License / Access Terms:** Public Government Statutory Document.
- **Geographic Coverage:** National and State Jurisdictions (India).
- **Update Frequency:** Annual statutory revisions.
- **Key Schema Fields:**
  - `item_code`: Standard classification code (e.g. Sub-structure RCC, Road Sub-base).
  - `work_description`: Exact engineering work specification.
  - `unit_of_measure`: Metric ton, cubic meter, kilometer, labor-hour.
  - `unit_rate_inr`: Statutory base cost per unit.
- **Operational Role in DIRS:** Benchmarks the capital cost estimation engine in `recovery_projects.estimated_cost`, multiplying physical quantities by official SOR rates plus a transparent contingency factor.

---

### 2.5 OpenStreetMap (OSM) Critical Infrastructure Vectors
- **Publishing Authority:** OpenStreetMap Foundation & Humanitarian OpenStreetMap Team (HOT).
- **Verified Access Link:** [OpenStreetMap Foundation](https://www.openstreetmap.org/)
- **License / Access Terms:** Open Database License (ODbL 1.0).
- **Geographic Coverage:** Global.
- **Update Frequency:** Continuous crowd-sourced mapping.
- **Key Schema Fields:**
  - `highway`: Road classification (`primary`, `secondary`, `tertiary`, `residential`).
  - `amenity`: Hospital, clinic, school, police, fire station.
  - `power`: Sub-station, generator, power tower.
  - `bridge`: Structural span attributes.
- **Known Limitations in DIRS:** Volunteer mapping coverage varies across rural jurisdictions. Used exclusively as a baseline geometric reference layer; never used as certified structural damage ground truth.

---

## 3. Category B: Candidate Future Integrations (Roadmap Boundary)

The following datasets represent high-value potential integrations identified for post-Phase 6 enhancement. **DIRS explicitly clarifies that none of these external data streams are currently integrated or active in the repository:**

| System / Provider | Intended Capability | Data Format / Protocol | Geographic Coverage | Reason for Phased Roadmap Placement |
| :--- | :--- | :--- | :--- | :--- |
| **Copernicus Emergency Management Service (EMS)** | Satellite InSAR interferometric subsidence and flood inundation extent. | GeoTIFF / WMS Raster | Global | Requires licensed European Space Agency API credentials and high-bandwidth raster pipelines. |
| **ISRO Bhuvan Disaster Services** | National flood hazard zonation and cyclone coastal inundation maps. | OGC WMS/WFS Services | India | Requires official institutional API partnership and security whitelisting. |
| **NASA FIRMS** | Near-real-time thermal satellite fire anomaly detection (MODIS/VIIRS). | REST JSON / CSV Feed | Global | High latency ($3\text{ hours}$) and low spatial resolution ($375\text{ m}$); unsuitable for urban building damage. |
| **State PWD Enterprise ERP** | Live contractor billing, e-tendering, and treasury voucher disbursements. | SOAP / REST Enterprise API | Regional Jurisdictions | Proprietary government intranet boundary; mocked via official Sanction Order inputs in Phase 6. |

---

## 4. Empirical Anti-Fabrication Safeguards

1. **Synthetic Data Must Be Explicitly Stamped:**
   Any benchmark dataset or simulation state generated for algorithm testing must include:
   - Database field: `is_simulated = TRUE`
   - Manifest metadata: `"data_provenance": "SYNTHETIC_CALIBRATED_BENCHMARK"`
2. **Separation of Estimates and Actuals:**
   - Modeled cost: `estimated_cost DOUBLE PRECISION`
   - Realized cost: `actual_expenditure DOUBLE PRECISION`
   The system rejects any automated overwrite of `actual_expenditure` by the optimization solver.
3. **Traceability of Official Decisions:**
   Project budget approvals must store the authenticated officer's `user_id`, digital timestamp, and a mandatory `sanction_order_number` corresponding to an administrative government budget voucher.
