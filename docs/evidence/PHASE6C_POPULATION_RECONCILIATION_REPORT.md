# DIRS Phase 6C — Population Reconciliation & De-duplication Intelligence Report

## 1. Executive Summary

In post-disaster environments, humanitarian assistance distribution faces major vulnerabilities from fragmented data collection: multiple NGOs, municipal teams, and volunteer groups conduct uncoordinated household surveys, resulting in duplicated beneficiary records, conflicting damage severity estimates, and inflated displacement claims.

Phase 6C implements the `PopulationReconciliationService`, providing an automated, mathematically sound reconciliation and conflict detection engine designed to unify multi-source beneficiary observations without double-counting.

---

## 2. Core Methodologies & Algorithms

### 2.1 Salted Cryptographic De-duplication Clustering
Field observations containing beneficiary identifiers (national ID, ration card, voter ID) are hashed using a fixed server-side salt:
$$\text{Digest} = \text{SHA256}(\text{beneficiary\_id} \parallel S_{\text{recovery}})$$
- Records with identical digests are clustered into candidate de-duplication sets.
- Each cluster is assigned a deterministic or tracking cluster identifier (`CLUSTER-<UUID>`).
- Redundant records within the same cluster are pruned from aggregate relief tallies, preventing duplicate resource allocation.

### 2.2 Multi-Observer Conflict Detection
When different observers file conflicting reports for the same facility or beneficiary, the system detects and flags discrepancies rather than silently averaging them:
1. **Severity Discrepancy**:
   If reported damage levels differ (e.g., Observer A reports `DESTROYED` while Observer B reports `MODERATE`), the record is flagged with `conflict_type = "DAMAGE_LEVEL_DISCREPANCY"`.
2. **Cost Estimation Variance**:
   If cost estimates diverge by more than 25%:
   $$\frac{|\text{Cost}_1 - \text{Cost}_2|}{\max(\text{Cost}_1, \text{Cost}_2)} > 0.25$$
   The discrepancy is flagged with `conflict_type = "COST_ESTIMATE_DIVERGENCE"`.
3. **Displaced Person Variance**:
   If reported displaced person numbers within the same household vary by more than 2 persons, a household discrepancy is flagged.

### 2.3 Unresolved Conflict Quarantine
Conflicting records are marked with `reconciliation_status = "CONFLICT_DETECTED"`. These records are quarantined from automated resource disbursement queues until an authorized Government Engineer or Recovery Coordinator conducts a physical field verification and signs off on an engineering verification override.

---

## 3. Census Consistency & Over-Capacity Enforcement

The reconciliation engine aggregates unique, deduplicated household records per ward and verifies against baseline demographic caps:
$$\text{Reconciled Displaced}(w) = \min\left(\sum_{h \in \text{Unique HH}(w)} \text{Displaced}(h), \;\text{Census Baseline}(w)\right)$$
- If the aggregated displacement exceeds the official census baseline:
  - `census_overcapacity_flag` is set to `true`.
  - An over-capacity alert is included in the response detailing the percentage exceedance:
    $$\text{Exceedance Pct} = \frac{\text{Reported} - \text{Baseline}}{\text{Baseline}} \times 100\%$$
  - Reconciled numbers are capped at the baseline to prevent fraudulent relief distribution.

---

## 4. Empirical Test Verification

The service was audited against multi-source simulated field observations in `tests/backend/test_phase6c_damage_needs.py`:
- **Scenario A: Identical Beneficiary Duplication**:
  - Observer A (Volunteer) and Observer B (NGO) both submit claims for beneficiary `AADHAAR-TIRUVALLUR-4401`.
  - Result: Detected 1 duplicate candidate group; redundant count = 1; unique beneficiaries = 1. Deduplication rate = 100%.
- **Scenario B: Severe Damage Conflict**:
  - Observer A reports `DESTROYED` with reconstruction cost INR 1,200,000.
  - Observer B reports `MODERATE` with reconstruction cost INR 400,000.
  - Result: Identified 1 unresolved conflict item; flagged `DAMAGE_LEVEL_DISCREPANCY` and cost variance of 66.7%. Correctly quarantined for human review.
- **Scenario C: Census Baseline Enforcement**:
  - Aggregated displaced persons capped at ward ceiling; over-capacity flag asserted correctly.
