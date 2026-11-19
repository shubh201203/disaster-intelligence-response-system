# DIRS Phase 6D-B: Operations, Resource Limits & System Limitations

**Subsystem:** Disaster Intelligence and Response System (DIRS)  
**Phase:** 6D-B — Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine  
**Milestone:** Milestone 6 — Final Architecture Treatise & Permanent Freeze  
**Status:** Certified & Frozen  
**Date:** November 2026  

---

## 1. Operating Parameters & Boundary Specifications

The Phase 6D-B engine is engineered with strict, verified mathematical boundaries to ensure predictable resource consumption and operational safety:

| Parameter | Minimum | Maximum Cap | Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **Candidate Projects ($N$)** | 1 | 500 | Pydantic validator throws `CANDIDATE_CEILING_EXCEEDED` (HTTP 422) if $N > 500$. |
| **Planning Horizon ($T$)** | 1 period | 120 periods | Pydantic bounds validator rejects $T < 1$ or $T > 120$. |
| **Solver Search Workers** | 1 worker | 16 workers | Bounded in request schema; default: 4 threads. |
| **CP-SAT Search Timeout Cap** | 1.0 s | 120.0 s | Validated in `RecoveryOptimizationService`; rejects requests with `max_solve_time_seconds > 120.0s`. |
| **Axios Client Timeout** | 130,000 ms | 130,000 ms | Client terminates HTTP connection at 130s with `SOLVER_TIMEOUT`. |
| **Random Search Seed** | 0 | $2^{31} - 1$ | Fixed at `seed = 42` for 100% deterministic reproducibility. |

---

## 2. Infrastructure & Compute Sizing

### Production Environment Sizing:
- **CPU:** 4 dedicated vCPUs (x86_64 or ARM64) to support multi-threaded CP-SAT search workers.
- **Memory (RAM):** 4 GB RAM minimum; 8 GB recommended for concurrent scenario evaluations.
  - Audited stress testing ($N=500, T=120$) consumes between 95 MB and 131 MB of true OS process Resident Set Size (RSS), accounting for the native C++ solver and worker pools.
- **Operating System:** Linux (Ubuntu 22.04 LTS / Debian 12), Windows Server 2022, or containerized Docker image.
- **Runtime Dependencies:**
  - Python 3.11+
  - Google OR-Tools 9.8+
  - FastAPI 0.110+
  - Pydantic v2.6+

---

## 3. Timeout Semantics & Latency Dynamics

### 3.1 Search Timer vs. End-to-End Service Execution Time
- **Search Timer Scope:** The parameter `max_solve_time_seconds` passed to Google OR-Tools CP-SAT (`solver.parameters.max_time_in_seconds`) applies strictly to the branch-and-bound search phase within the native C++ engine.
- **Pre-Search Overhead:** Prior to the search phase, the service must perform Python DTO conversion, candidate validation, fixed-point CCU scaling, topological sorting, CPM bounds calculation, Python AST model construction (generating up to 60,000 variables and thousands of linear constraints for large horizons), and native C++ model presolve.
- **No Guaranteed 120s End-to-End Ceiling:** The 120-second configured solver ceiling applies strictly to the CP-SAT search parameter. **It must not be represented as a guaranteed 120-second end-to-end API response ceiling.**
- **Absence of Server-Side Request Timeout:** Inspection of the backend implementation confirms that **no separate end-to-end server/request timeout (e.g., ASGI middleware or Uvicorn global request timeout) is established by the current evidence.** The only server-side timeout enforcement is the parameter validation cap rejecting `max_solve_time_seconds > 120.0s`.

### 3.2 Tier 4 Empirical Latency & Synchronous Non-Certification
- **Audited Latency:** During Tier 4 benchmark evaluation ($N=500, T=120$), the solver search timer was configured to `60.0s`. Due to Python model construction and native C++ presolve overhead, internal solve duration reached **173.19s**, and total end-to-end service latency was **176.96s**.
- **Interactive Synchronous Non-Certification:** Because the frontend Axios client enforces an immutable `130,000 ms` (130s) request timeout, **the current synchronous architecture does not certify Tier 4 ($N=500, T=120$) for interactive HTTP requests.** Submitting a 500-candidate, 120-period scenario via the web UI will exceed the 130s client timeout and trigger a client-side `SOLVER_TIMEOUT` error.
- **Certified Synchronous Envelope:** Interactive synchronous HTTP evaluation is certified strictly for workloads up to **Tier 3 ($N \le 200, T \le 60$)**, which complete end-to-end in approximately 61.2 seconds.

---

## 4. Tier 4 Capability Classification: Offline Benchmark Only

- **Benchmark Context:** Tier 4 was evaluated exclusively through the local in-process Python benchmark runner (`scratch/run_phase6d_benchmarks.py`).
- **No Production Batch Processing Feature:** The successful completion of Tier 4 demonstrates the algorithmic scalability and memory efficiency of the mathematical formulation, **not a demonstrated production asynchronous batch-processing feature.**
- **Out-of-Scope Architecture:** Job queues (e.g., Celery, Redis, RQ), task polling mechanisms, background daemon workers, and asynchronous job orchestration remain entirely outside the completed Phase 6D-B implementation.
- **Future Work:** Any future asynchronous batch-processing capability for large-scale portfolios requires a separately authorized implementation phase.

---

## 5. System Behaviors & Graceful Degradation

### 5.1 Incomplete Proof Handling (FEASIBLE vs. UNKNOWN)
If CP-SAT reaches its search time limit without proving global optimality:
- **Incumbent Usability (FEASIBLE):** If at least one valid schedule was found during search, the solver returns status `FEASIBLE` alongside the incumbent schedule, objective value, conservative best bound, and the exact optimality gap (e.g., $1.11\%$). The schedule is fully usable.
- **No Solution Found (UNKNOWN):** If no feasible schedule was discovered before the time limit expired, status `UNKNOWN` is returned with an empty schedule.

### 5.2 Infeasibility Handling
When scenario constraints are contradictory:
- The solver returns status `INFEASIBLE` with an empty schedule array (`[]`).
- The 4-tier diagnostic engine executes, isolating proven root causes or minimal conflict cores.
- The UI suppresses schedule visualizations and renders the Infeasibility Diagnostics View.

### 5.3 Zero Database Mutation Guarantee
The optimization engine is strictly analytical and in-memory. It executes 0 database write transactions, ensuring zero corruption of operational tables.
