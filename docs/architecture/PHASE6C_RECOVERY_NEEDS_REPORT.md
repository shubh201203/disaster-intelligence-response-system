# DIRS Phase 6C — Multi-Sectoral Recovery Needs & Demographic Conservation Report

## 1. Executive Summary

Phase 6C of DIRS implements the structured multi-sectoral recovery needs intelligence framework formulated in Phase 6A. It ensures that humanitarian demand quantification is physically consistent, demographic-conserving, non-negative, and strictly bound by verified census baseline populations.

### Core Mathematical & Operational Principles
1. **Multi-Sectoral Coverage**: Full support for the six vital post-disaster recovery sectors:
   - `HOUSING`: Permanent and semi-permanent residential reconstruction, structural reinforcement, transitional shelter.
   - `WASH`: Potable drinking water distribution, mobile filtration units, sanitation facilities, water main restoration.
   - `HEALTH`: Emergency trauma care, chronic medication replenishment, mobile clinics, psychiatric support.
   - `EDUCATION`: School building repair, temporary instructional tents, textbook and digital learning aid distribution.
   - `LIVELIHOODS`: Direct micro-grant assistance, artisanal tool replacement, agricultural and fishing kit disbursal.
   - `ESSENTIAL_SERVICES`: Municipal debris clearance, hazardous waste removal, municipal drainage de-silting.
2. **Demographic Conservation Identity**: Every need assessment recording demographic splits must strictly satisfy:
   $$N_{\text{displaced}} = N_{\text{GEN}} + N_{\text{ACC}} + N_{\text{MED}} + N_{\text{MED\_ACC}}$$
   Where:
   - $N_{\text{GEN}}$: General displaced population without specialized mobility or medical needs.
   - $N_{\text{ACC}}$: Persons requiring accessibility accommodations (wheelchairs, ramps, specialized transit).
   - $N_{\text{MED}}$: Persons requiring active daily medical intervention (dialysis, insulin, oxygen, palliative care).
   - $N_{\text{MED\_ACC}}$: Persons requiring both intensive medical care and accessibility accommodations.
3. **Operational Census Baseline & Conflict Review (DEF-6C-CEN-01 & DEF-6C-CEN-02)**:
   - **Provenance Notice**: No authoritative statutory census dataset (such as Census of India or Greater Chennai Corporation official ward registries) is bundled. The `census_baseline_population` is an operational estimate supplied by the caller during ingestion.
   - **Soft-Flagging at Ingestion**: When an individual need report has $N_{\text{affected}} > N_{\text{census\_baseline}}$, the API accepts the field report to preserve critical on-ground observations, but flags `exceeds_census_cap = True` in metadata and logs an audit warning.
   - **Quarantine at Reconciliation**: During population reconciliation (`reconcile_population`), if aggregate displaced persons exceed the supplied ward baseline, the engine automatically attaches a `CONF-CENSUS-OVERCAP` conflict item, setting status to `FLAGGED_FOR_HUMAN_REVIEW` to quarantine unverified spikes from automated relief distribution.

---

## 2. Demographic Breakdown & Privacy Preservation Architecture

### 2.1 Demographic Conservation Invariant Verification
The Pydantic validator `DemographicBreakdown.validate_conservation` and service-level checks enforce exact demographic conservation:
```python
calculated_total = (
    self.general_need +
    self.accessibility_need +
    self.medical_need +
    self.med_accessibility_need
)
if calculated_total != self.total_displaced_persons:
    raise ValueError(
        f"Demographic conservation violation: components sum to {calculated_total}, "
        f"expected total_displaced_persons={self.total_displaced_persons}"
    )
```

### 2.2 Beneficiary Identity Pseudonymization (DEF-6C-SEC-01)
To comply with humanitarian privacy mandates (Do No Harm) and prevent surveillance of displaced persons:
- **Salted SHA-256 Hashing**:
  $$\text{Hash} = \text{SHA256}(\text{salt} \parallel \text{raw\_beneficiary\_id} \parallel \text{salt})$$
  The raw identity is hashed using the explicitly configured server-side cryptographic secret `BENEFICIARY_HASH_SALT`.
  - **Fail-Closed Security**: Insecure fallback defaults have been completely removed. If `BENEFICIARY_HASH_SALT` is absent or empty, `hash_beneficiary_id` strictly raises `RuntimeError`, failing closed and preventing unkeyed or default-keyed hashing.
  - **Pseudonymization Distinction**: The hashing is deterministic to enable cross-agency deduplication; therefore, it provides cryptographic pseudonymization, not full irreversible anonymization.
- **Name Masking**:
  Individual beneficiary names are transformed prior to storage (e.g., `"Sundararajan"` $\to$ `"S***n"`, `"Kavitha"` $\to$ `"K***a"`).
- **Public vs. Private Exposure**:
  - Government / Official queries receive pseudonymized beneficiary hashes for cross-departmental reconciliation.
  - Public situation endpoints completely scrub all household identities, reporting only ward-level aggregations.

---

## 3. Mathematical Consistency & Validation Suite

| Scenario | Input Specification | Expected Outcome | Observed Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Valid Demographic Split** | Displaced = 120 (GEN=80, ACC=20, MED=15, MED_ACC=5) | Accepted (HTTP 201) | Recorded with JSON notes | **PASS** |
| **Demographic Sum Mismatch** | Displaced = 100 (GEN=60, ACC=20, MED=10, MED_ACC=5, Sum=95) | Rejected (HTTP 422) | Pydantic validation rejected | **PASS** |
| **Negative Component** | General Need = -10 | Rejected (HTTP 422) | `ge=0` schema bound caught | **PASS** |
| **Census Exceedance** | Displaced = 20,000 against Supplied Baseline = 15,000 | Accepted & Flagged | `exceeds_census_cap = True`, audited | **PASS** |
| **Census Overcap Conflict** | Aggregated Ward Displacement > Baseline Ceiling | Quarantined | `CONF-CENSUS-OVERCAP` flagged | **PASS** |
| **Missing Salt Fails Closed** | `BENEFICIARY_HASH_SALT` unset or empty | RuntimeError | Insecure fallbacks blocked | **PASS** |
| **Salted Hash Invariance** | Beneficiary `"AADHAAR-8901"` submitted twice | Deterministic Hash | Identical 64-char hex digest | **PASS** |
| **Role Restriction** | Volunteer submits `/needs/structured` | Rejected (HTTP 403) | Citizen/Volunteer blocked | **PASS** |

---

## 4. Architectural Integration & Relational Storage

Demographic breakdowns and structured sector requirements are seamlessly persisted in the frozen Phase 6B `RecoveryNeed` entity without requiring relational migrations:
- `ward_code`: Administrative boundary code (e.g., `"WARD-04"`).
- `sector`: Normalized sector enum (`HOUSING`, `WASH`, `HEALTH`, `EDUCATION`, `LIVELIHOODS`, `ESSENTIAL_SERVICES`).
- `affected_households`, `displaced_persons`, `potable_water_demand_liters_day`, `temporary_shelter_units_needed`, `livelihood_support_households`.
- `beneficiary_id_hash`: Pseudonymized SHA-256 hex digest.
- `household_head_name_masked`: Privacy-masked representative name.
- `reconciliation_notes`: Structured JSON containing the validated `demographic_breakdown` dictionary, ensuring zero schema deviation while providing full analytical fidelity.
