# DIRS Phase 6C — Census & Population Provenance Forensic Audit

**Audit Date:** 2026-11-16T01:58:30+05:30  
**Auditor Role:** Independent Humanitarian Data Governance Specialist & Forensic Data Auditor  
**Target Services:** `RecoveryNeedsService` ([`recovery_needs_service.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/recovery_needs_service.py)) & `PopulationReconciliationService` ([`population_reconciliation.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/population_reconciliation.py))

---

## 1. Executive Summary

A thorough investigation of the backend codebase, relational schema, and seed files reveals that **no external or authoritative census dataset is bundled, stored, or queried by the DIRS application**:
- There are no Census of India (2011/2021) data tables or GeoJSON shapefiles.
- The `census_baseline_population` value is entirely supplied as a runtime integer parameter in the ingestion payload of `/api/v1/recovery/needs/structured`.
- While the system successfully prevents demographic conservation identity violations and flags potential census over-capacity, the baseline population numbers are synthetic/user-provided and cannot be cited as authoritative governmental statistics.

---

## 2. Census Data Provenance Investigation

| Audit Dimension | Forensic Evidence & Finding |
| :--- | :--- |
| **Dataset Name** | None. No published census dataset (e.g., Census of India or District Census Handbook) is integrated. |
| **Publisher & License** | N/A. No government open-data license (e.g., Open Government Data License - India) is present. |
| **Reference Year** | Unspecified. Not bound to any statutory census year (e.g., 2011 or projected 2021/2026). |
| **Geographic Level** | Ward-level strings (`"WARD-01"`, `"WARD-04"`), but without administrative cadastral mapping. |
| **Data Nature** | **Synthetic / User-Supplied Parameter**: The value of `census_baseline_population` is entered by the API caller during `StructuredRecoveryNeedCreate`. |
| **Persistence Mechanism** | Persisted directly to `recovery_needs.census_baseline_population` (Column added in Phase 6B). |

---

## 3. Code Trace of Population Ceilings & Over-Capacity Handling

### 3.1 Need Creation Gate (`recovery_needs_service.py`)
In `RecoveryNeedsService.create_structured_need`:
```python
# Lines 93-108
census_cap = data.census_baseline_population
if census_cap <= 0:
  raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Census baseline population must be greater than zero",
  )

exceeds_census = total_affected > census_cap
demographic_dict = {
    "gen": data.affected_population_gen,
    "acc": data.affected_population_acc,
    "med": data.affected_population_med,
    "med_acc": data.affected_population_med_acc,
    "total_affected": total_affected,
    "exceeds_census_cap": exceeds_census,
}
```
**Forensic Observation**:
When an individual need report exceeds the user-supplied census cap ($N_{\text{affected}} > N_{\text{census}}$), the API **does not reject** the request with HTTP 422. Instead, it accepts the submission, flags `exceeds_census_cap = True` in metadata, and logs `"exceeds_census": true` to `AuditService`. This contradicts the claim in `docs/PHASE6C_RECOVERY_NEEDS_REPORT.md` Section 3 which stated that census exceedance was rejected with HTTP 422.

### 3.2 Population Reconciliation Gate (`population_reconciliation.py`)
In `PopulationReconciliationService.reconcile_population`:
```python
# Lines 149-160
census_baseline = max(n.census_baseline_population for n in needs)
utilization_pct = (
    round((total_reconciled_pop / census_baseline * 100.0), 2)
    if census_baseline > 0
    else 0.0
)

if utilization_pct > 100.0:
  unresolved_conflicts.append(
      UnresolvedConflictItem(
          cluster_id="CONF-CENSUS-OVERCAP",
          conflicting_need_ids=[n.id for n in needs],
          reason=(
              f"Reconciled affected population ({total_reconciled_pop}) exceeds"
              f" ward census baseline cap ({census_baseline}) by"
              f" {utilization_pct - 100.0:.1f}%"
          ),
          requires_human_review=True,
      )
  )
```
**Forensic Observation**:
- If all needs in a query have `census_baseline_population = 0` (which is prohibited at ingestion, but could occur if unpopulated legacy records exist), `census_baseline` evaluates to 0 and `utilization_pct` defaults to `0.0`. It does not raise a divide-by-zero exception.
- When aggregated reconciled population exceeds the maximum stated baseline cap, the system appends a conflict item (`cluster_id="CONF-CENSUS-OVERCAP"`) and marks the reconciliation status as `FLAGGED_FOR_HUMAN_REVIEW`.

---

## 4. Demographic Conservation Invariant Verification

Phase 6A established the demographic conservation identity:
$$N_{\text{displaced}} \le N_{\text{total\_affected}} = N_{\text{GEN}} + N_{\text{ACC}} + N_{\text{MED}} + N_{\text{MED\_ACC}}$$

### Code Enforcement:
1. **Pydantic Validation** ([`app/schemas/recovery.py`, lines 375-385](file:///c:/Users/shubh/Downloads/DIRS/backend/app/schemas/recovery.py#L375-L385)):
   Rejects negative figures via `ge=0` bounds on all population components.
2. **Service Validation** ([`recovery_needs_service.py`, lines 45-74](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/recovery_needs_service.py#L45-L74)):
   - Verifies all four components are non-negative.
   - Calculates `total_affected = gen + acc + med + med_acc`.
   - Strictly enforces that `displaced_persons <= total_affected`. If violated, raises `HTTP 400 Bad Request`.
3. **Double-Count Prevention**:
   In `PopulationReconciliationService`, records sharing identical salted beneficiary hashes (`beneficiary_id_hash`) are grouped together. For duplicate submissions of the same household, only the latest verified record is accumulated into `reconciled_hh_count` and `reconciled_disp_count`. Redundant records are eliminated from aggregate totals.

---

## 5. Material Findings & Risk Assessment

- **Finding DEF-6C-CEN-01 (Documentation Inaccuracy on Census Rejection)**:
  - *Location*: `docs/PHASE6C_RECOVERY_NEEDS_REPORT.md` (Section 3).
  - *Severity*: **LOW (Documentation Claim vs Implementation)**.
  - *Description*: The report claimed that submissions exceeding census caps are rejected with HTTP 422. In reality, the service ingests them with `exceeds_census_cap = True` and flags them during reconciliation (`CONF-CENSUS-OVERCAP`) for human engineering review. This design is actually operationally superior for disaster response (preserving field reports rather than dropping data), but the documentation must reflect the actual soft-quarantine behavior.
- **Finding DEF-6C-CEN-02 (Synthetic Census Baseline Acknowledgment)**:
  - *Location*: System-wide census baseline claims.
  - *Severity*: **MEDIUM (Data Governance Requirement)**.
  - *Description*: Baselines are user-entered parameters rather than validated statutory census records. The system must never claim authoritative census grounding until official census tables are connected.
