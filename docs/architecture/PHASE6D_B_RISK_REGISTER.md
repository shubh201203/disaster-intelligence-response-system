# DIRS Phase 6D-B — Milestone 0: Risk Register & Forensic Mitigation Protocol
## Comprehensive Vulnerability Analysis, Mathematical Guardrails, and Regression Safeguards

**Document ID:** `DIRS-PHASE6D-B-M0-04`  
**Phase:** Phase 6D-B (Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine)  
**Milestone:** Milestone 0 (Forensic Preflight & Schema Compatibility)  
**Lead Authors:** Principal Software Architect, Optimization Systems Engineer, Technical QA Lead  
**Date of Audit:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Executive Summary

This document establishes the comprehensive risk register and forensic mitigation protocol for Phase 6D-B. Implementing discrete multi-period optimization and multi-criteria prioritization within an enterprise disaster response platform introduces risks across mathematical correctness, integer programming scalability, data integrity, regulatory governance, and regression stability. 

Every identified risk is assigned a severity rating, a structural root cause analysis, an automated mitigation strategy, and a concrete verification gate to guarantee that system safety and operational integrity are preserved.

---

## 2. Comprehensive Risk Assessment Matrix

| Risk ID | Risk Description | Severity | Likelihood | Impact Area | Architectural Mitigation Strategy | Verification & Gating Protocol |
| :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| **RSK-6D-01** | **CP-SAT Integer Scaling Overflow:** Financial capital costs in INR (e.g. hundreds of millions) scaled to integers overflow standard 32/64-bit integer domains in CP-SAT. | **HIGH** | Medium | Optimization Engine | Express all currency values in standardized Lakh INR ($10^5$) with integer scale factor $100$ (representing rupees to the nearest thousand). Cap intermediate variable domains at $10^{12}$. | Automated unit tests in Milestone 2 testing multi-crore budgets without integer overflow exceptions. |
| **RSK-6D-02** | **Solver Timeout / Infinite Search:** Large recovery instances ($N \ge 100$) with dense precedence DAGs fail to prove optimality within acceptable interactive latency. | **HIGH** | Medium | System Latency & UX | Enforce deterministic timeout guard (`solver.parameters.max_time_in_seconds = 60.0`). Return best feasible solution found with explicit optimality gap. If timed out, label status `FEASIBLE_TIMED_OUT`. | Milestone 2 benchmark suite testing $N=10, 50, 100$ with hard 60s timeout termination. |
| **RSK-6D-03** | **Silent Constraint Relaxation:** Solver heuristic or advisor softens precedence, budget solvency, or safety mandates to escape an `INFEASIBLE` state. | **CRITICAL** | Low | Operational Safety | Absolute architectural prohibition. Hard constraints (precedence, solvency, atomicity, safety filter) have zero slack variables in the CP-SAT model. | Milestone 3 negative tests proving that impossible budgets return `INFEASIBLE`, never partial schedules. |
| **RSK-6D-04** | **Perverse Demographic Deprioritization:** Unknown census baselines or unsegregated vulnerable populations penalized by assigning arbitrary minimum scores or dividing by NULL. | **HIGH** | Medium | Humanitarian Equity | Implement bifurcated formulation: if baseline is unknown, scale observed headcount $\psi$ against reference benchmark $\psi_{\text{ref}} = 500$ without dividing by NULL. Compute lower bounds for unsegregated data. | Milestone 1 unit tests verifying identical $\psi$ across unknown baselines yields well-defined scores $\in [0, 1]$. |
| **RSK-6D-05** | **Precedence Orphan Successor Scheduling:** Highly attractive successor project ($w_j=1$) scheduled without its mandatory prerequisite ($w_i=0$). | **CRITICAL** | Low | Physical Construction Law | Enforce structural selection co-requisite $w_j \le w_i$ for every mandatory edge $(i, j)$ in CP-SAT and heuristic validators. | Milestone 1 and 2 tests proving successor is rejected when predecessor is unselected. |
| **RSK-6D-06** | **Calendar Cost Indexing Desynchronization:** Conflating internal project execution age $\tau$ with global calendar period $t$, causing premature or delayed cash-flow charges. | **HIGH** | Medium | Financial Accounting | Implement explicit convolution mapping: $C_{j, t} = \sum_{s=\max(1, t-d_j+1)}^t \gamma_{j, t-s+1} x_{j, s}$. Enforce lifetime cost reconciliation: $\sum_t C_{j, t} = w_j c_j$. | Milestone 1 hand-calculated unit tests verifying start at $t=3$, duration 3 spends exactly across $t=3, 4, 5$. |
| **RSK-6D-07** | **Accidental Database Migration / Schema Drift:** Code modifications introducing new tables, columns, or altering Alembic head revision `phase6b_recovery_foundation`. | **CRITICAL** | Low | Database Integrity | Absolute Zero-Migration Policy. All persistent fields mapped to existing Phase 6B columns (`time_indexed_cost_profile`, `is_critical_path`, etc.). CI/CD checks assert Alembic head is unchanged. | Automated migration check asserting `script_dir.get_current_head() == "phase6b_recovery_foundation"`. |
| **RSK-6D-08** | **Licensure Misrepresentation Liability:** User accounts with `role == "GOVT"` represented as licensed structural engineering certifications, creating legal liability. | **HIGH** | Low | Legal & Governance | Accurate terminology enforced across all API responses, schemas, and UI manifests: *Government Administrative Verification* only. Disbursement held pending licensed report. | Milestone 4 schema audit verifying qualification disclaimer strings present in all optimization responses. |
| **RSK-6D-09** | **Regression of Existing Phases 1–6C:** New recovery code destabilizing existing endpoints, models, or causing any of the 382 baseline tests to fail. | **CRITICAL** | Medium | System Stability | Primary implementation confined strictly to `backend/app/recovery/services/`. Phase 1–5G engines and Phase 6C services are completely frozen. | Milestone 5 full regression run asserting 382/382 baseline tests pass without exception. |
| **RSK-6D-10** | **Unauthorized Human Schedule Overrides:** Ordinary users or automated processes bypassing solver outputs and approving unfeasible schedules. | **HIGH** | Low | System Security | Enforce RBAC gates: only `GOVT` or `ADMIN` roles may submit overrides. Mandatory justification text ($\ge 20$ chars) logged immutably to `RecoveryOverrideLog`. | Milestone 3 and 4 security tests asserting non-GOVT override attempts receive HTTP 403 Forbidden. |

---

## 3. Forensic Guardrails & Fail-Closed Protocols

1. **Solver Fail-Closed Policy:**
   If the CP-SAT solver encounters an infeasible formulation, it returns status `INFEASIBLE` with structured diagnostics. It is strictly forbidden from generating a partial, corrupted, or unbacked schedule.
2. **Schema Drift Fail-Closed Policy:**
   Any attempted invocation of Alembic upgrade, column addition, or raw SQL table alteration triggers an immediate build halt and test failure.
3. **Disbursement Hold Policy:**
   Projects elevated to Tier 1 via operational triage are assigned status `HOLD_PENDING_QUALIFIED_INSPECTION`. Capital contracts cannot tender until an authorized official attaches an accredited structural inspection report.

---
*End of DIRS Phase 6D-B Milestone 0 Risk Register.*
