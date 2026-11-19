# DIRS Phase 6F / Accelerated Programme WP2: Census Reconciliation & Conflict Detection

**Document Version:** 1.0.0  
**Service:** `PopulationReconciliationService`  
**Location:** `backend/app/recovery/services/population_reconciliation.py`  

---

## 1. Overview & Privacy Safeguards

In post-disaster scenarios, beneficiary reports originate from multiple conflicting sources: NGO field surveys, shelter registries, municipal aid applications, and self-reported claims. 

`PopulationReconciliationService` achieves multi-record deduplication and conflict tracking without violating citizen privacy:
1. **Salted PII Hashing:** Beneficiary national IDs and biometric IDs are salted with `BENEFICIARY_HASH_SALT` and hashed using HMAC-SHA256. Raw identification numbers are never persisted or returned across API boundaries.
2. **Name Masking:** Household head names are strictly masked in output DTOs (e.g. `J*** D***`).

---

## 2. Reconciliation & Conflict Detection Workflow

```
                                +-------------------------------+
                                |  Raw RecoveryNeed Records     |
                                |  - Ward Code / District       |
                                |  - beneficiary_id_hash        |
                                |  - displaced_persons          |
                                +---------------+---------------+
                                                |
                                                v
                               +--------------------------------+
                               | Group by beneficiary_id_hash   |
                               +----------------+---------------+
                                                |
                        +-----------------------+-----------------------+
                        |                                               |
                        v                                               v
             [Single Observation]                             [Multiple Observations]
             - Clean entity                                   - Duplicate candidate group flagged
             - No conflict                                    - Inspect reported counts (HH, Displaced)
                                                                        |
                                                +-----------------------+-----------------------+
                                                |                                               |
                                        [Counts Match]                                 [Counts Disagree]
                                        - Deduplicated cleanly                          - UNRESOLVED CONFLICT:
                                        - Use latest timestamp                            CONF-{hash} flagged
                                                                                        - Human review escalated
                                                |                                               |
                                                +-----------------------+-----------------------+
                                                                        |
                                                                        v
                                                       +--------------------------------+
                                                       |   Census Baseline Verification |
                                                       |   Sum(Pop) vs P_census         |
                                                       +----------------+---------------+
                                                                        |
                                                +-----------------------+-----------------------+
                                                |                                               |
                                        [Sum <= P_census]                               [Sum > P_census]
                                        - Census utilization normal                     - CONF-CENSUS-OVERCAP
                                        - Status: FULLY_RECONCILED                       - Discrepancy metric logged
```

---

## 3. Discrepancy & Conflict Classification

### 3.1 Duplicate Candidate Identification
When two or more needs records share an identical `beneficiary_id_hash`:
- Recorded in `duplicate_candidates` with cluster size and matching reason.
- Resolved via monotonic rule: the record with `is_reconciled=True` or the most recent `data_timestamp` is adopted for aggregation totals, eliminating double-counting.

### 3.2 Unresolved Observation Conflicts
When identical beneficiaries report divergent household or displaced headcount:
- Flagged as `CONF-{hash[:8]}`.
- Sets `requires_human_review = True`.
- Degrades reconciliation confidence score:
  $$\text{Confidence} = \max(50.0, \; 100.0 - 15.0 \times |\text{conflicts}|)$$

### 3.3 Census Cap Over-Utilization (`CONF-CENSUS-OVERCAP`)
When the aggregated reconciled affected population exceeds the ward census baseline:
$$\text{utilization\_pct} = \frac{\sum N_{\text{reconciled}}}{P_{\text{census}}} \times 100.0\%$$
- If $\text{utilization\_pct} > 100.0\%$:
  - Flagged as `CONF-CENSUS-OVERCAP`.
  - Discrepancy magnitude $(\text{utilization\_pct} - 100.0)\%$ is recorded in provenance summary.
  - Escalated to human disaster commissioner review.

---

## 4. Verification Evidence

Tested and verified in `tests/backend/test_phase6f_wp2_community_simulation.py`:
- `test_census_reconciliation_empty`: Empty area returns `EMPTY` with 100% confidence.
- `test_census_reconciliation_duplicates_and_conflicts`: Dual records with divergent displaced persons properly generate `CONF-` cluster, flag human review, and decay confidence score below 90%.
