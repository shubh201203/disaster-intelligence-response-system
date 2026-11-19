# DIRS Phase 6A — Data Strategy & Provenance Architecture
## Authority Classifications, External Baseline Catalog, and Empirical Integrity Standards

**Document ID:** `DIRS-PHASE6A-DOC-03`  
**System:** Disaster Intelligence and Response System (DIRS)  
**Classification:** DATA STRATEGY & SOURCE CATALOG  
**Author:** Principal Disaster-Management Systems Architect & Forensic Auditor  

---

## 1. Data Integrity and Provenance Mandate

Post-disaster recovery intelligence directly impacts human rehabilitation, public capital expenditure, and critical infrastructure resilience. Systems that misrepresent unverified synthetic data as empirical field observations or fabricate government budgets introduce unacceptable operational, financial, and legal hazards.

DIRS enforces a strict **Five-Tier Provenance Taxonomy**:
1. **Tier 1: Existing DIRS Live Operational Data** — Live transactional records persisted in PostgreSQL/PostGIS (incidents, shelters, volunteer tasks, acute resource logs).
2. **Tier 2: Government-Provided / Certified Data** — Official census statistics, Public Works Department (PWD) schedule of rates, certified infrastructure registries, approved recovery budget envelopes.
3. **Tier 3: Verified Open / Authoritative International Data** — Standard guidelines, manuals, and open geospatial vectors published by recognized agencies (UNDRR, UNDP, World Bank/GFDRR, UN OCHA, WHO, OpenStreetMap).
4. **Tier 4: Citizen and Field Volunteer Submissions** — Crowdsourced damage photos, household need surveys, and community status reports requiring human verification.
5. **Tier 5: Synthetic Calibrated Benchmark Data** — Algorithmic or procedurally generated scenarios used strictly for algorithm validation, stress-testing, and simulation. **Must be explicitly stamped `SYNTHETIC_CALIBRATED_BENCHMARK` and never conflated with live disaster records.**

---

## 2. Authoritative International and National Source Catalog

The following authoritative datasets, guidelines, and reference standards have been surveyed and documented for Phase 6 recovery planning:

| # | Publisher / Agency | Dataset / Standard Title | Document Reference / Verified Link | Geographic Coverage | Update Frequency | License / Access Terms | Key Schema Fields Utilized | Operational Role & Limitations in DIRS |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **UNDP / World Bank / EU** | Post-Disaster Needs Assessment (PDNA) Guidelines (Vols A & B) | [GFDRR PDNA Guidelines](https://www.gfdrr.org/en/publication/post-disaster-needs-assessments-guidelines) | Global Standard | Decennial revision | Open Access / Public Good | Sectoral damage categories, loss definitions, recovery needs equations, human recovery metrics | Methodological foundation for Domain B & C. Does not provide real-time automated data streams. |
| **2** | **UNDRR** | Sendai Framework for Disaster Risk Reduction (2015–2030) Priority 4 | [UNDRR Sendai Framework](https://www.undrr.org/implementing-sendai-framework/what-sendai-framework) | Global | Policy Framework | Open Access | Target 4 indicators (damage to critical infrastructure, basic service disruption), Build Back Better metrics | Defines recovery evaluation targets and resilience indicators for Domain H. |
| **3** | **UN OCHA (HDX)** | Humanitarian Data Exchange — Administrative Boundaries (COD-AB) | [HDX Portal](https://data.humdata.org/) | Global / National / District / Ward | Quarterly / As updated | Creative Commons Attribution (CC-BY) | `admin_level`, `boundary_polygon`, `pcode`, `census_population` | Used for spatial aggregation and preventing double-counting across overlapping zones. |
| **4** | **WHO** | Guidance for Post-Disaster Health System Rehabilitation | [WHO Emergency Guidelines](https://www.who.int/emergencies) | Global | Periodic | Open Access | Health facility damage tiers, cold chain restoration standards, water quality limits | Technical thresholds for prioritizing hospital and health center reconstruction. |
| **5** | **CPWD / State PWD** | Schedule of Rates (SOR) for Civil Infrastructure Works | State/National PWD Portals | India / Regional Jurisdictions | Annual / Bi-annual | Public Government Document | `item_code`, `work_description`, `unit_rate_inr`, `material_breakdown` | Benchmark pricing for reconstruction material and labor cost estimation in Domain D. |
| **6** | **OpenStreetMap (OSM)** | Critical Infrastructure Features (Overpass API / Geofabrik) | [OpenStreetMap Foundation](https://www.openstreetmap.org/) | Global / Regional | Real-time crowd-updated | ODbL (Open Database License) | `building:levels`, `highway`, `amenity:hospital`, `power:substation`, `bridge` | Baseline pre-disaster topological footprints for damage comparison. Subject to volunteer coverage gaps. |
| **7** | **NDMA (India)** | National Disaster Management Guidelines: Restoration of Lifelines | [NDMA Publications](https://ndma.gov.in/) | National (India) | Periodic Statutory | Public Government Document | Lifeline restoration hierarchies, seismic retrofitting standards, flood wall design codes | Authoritative reference ingested into DIRS RAG system for grounded recovery guidance. |

---

## 3. Classification of Recovery Data Entities

Every proposed data entity in Phase 6 is mapped to its provenance tier and verification requirements:

| Proposed Phase 6 Entity | Entity Scope | Provenance Tier | Verification & Authority Gate | Failure / Incomplete Data Fallback |
| :--- | :--- | :---: | :--- | :--- |
| **Recovery Assessment** | Multi-sector damage and loss audit per facility/zone. | Tier 2 or Tier 4 | Requires certified civil engineer sign-off (`GOVT` role). | Flagged as `UNVERIFIED_PROVISIONAL`; excluded from binding budget totals. |
| **Recovery Project** | Capital restoration project (e.g. Bridge Repair, School Reconstruction). | Tier 2 | Requires Executive Government Administrative Approval (`GOVT_ADMIN`). | Incomplete projects marked `DRAFT`; zero funds can be allocated. |
| **Restoration Dependency** | Precedence link in infrastructure graph ($A \rightarrow B$). | Tier 2 / Engineering Model | Validated by municipal utility engineer. | Default to independent sequencing if precedence unconfirmed. |
| **Material Scheduled Rate** | Unit cost per metric ton of steel/cement or road km. | Tier 2 / Tier 3 | Indexed to published official Schedule of Rates (SOR). | Marked with `PROVISIONAL_ESTIMATE` flag and $+20\%$ contingency buffer. |
| **Community Survey** | Household recovery progress and utility status. | Tier 4 | Filtered against duplicate submissions via unique household ID. | Statistical exponential confidence decay applied over time. |
| **Recovery Simulation** | What-if scenario parameters (budget shock, supply delay). | Tier 5 | Generated ephemerally in sandbox; deep-copy isolated. | Base records remain immutable; simulation results stamped with disclaimer. |

---

## 4. Empirical Integrity Safeguards

1. **No External Live API Dependencies for Core Solvers:** Optimization engines and critical path calculations must execute deterministically using persisted database entities and verified parameters. DIRS must never fail due to an unreachable third-party external server.
2. **Explicit Labeling of Estimates:** All financial figures derived from unit-rate multiplying must bear the database column name and UI indicator `estimated_cost` or `indicative_budget`. The label `actual_expenditure` is strictly restricted to audited invoices logged with government voucher references.
3. **Double-Count Prevention:** Beneficiary headcounts are normalized by census ward code and unique family identity. The sum of affected individuals in sub-projects within a ward cannot exceed the verified census population of that ward.
4. **Data Staleness & Expiration:** Community survey data and field assessments decay in confidence after 14 days without re-verification. The UI displays an amber warning badge for data older than 14 days and a red expired badge for data older than 30 days.
