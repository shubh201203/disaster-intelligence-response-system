# DIRS Phase 5D — Implementation Architecture Document

## 1. Core Component Architecture
The Multi-Commodity Resource Allocation Solver Engine comprises the following production files:

- **`backend/app/ai/optimization/allocation.py`**:
  - `ResourceAllocationEngine`: Google OR-Tools CP-SAT multi-commodity optimization solver.
  - `GreedyProximityAllocationEngine`: Baseline A heuristic solver.
  - `FCFSAllocationEngine`: Baseline B queue solver.
- **`backend/app/ai/optimization/benchmark_dataset.py`**:
  - `generate_dirs50_benchmark_dataset()`: Deterministic synthetic dataset generator calibrated against Sphere standards.
- **`backend/app/ai/optimization/service.py`**:
  - `ResourceAllocationService`: DB persistence service managing `OptimizationRun`, `OptimizationRecommendation`, `OptimizationOverrideLog`, and `AuditLog` integration with Government HITL approval workflow (`APPROVE`, `MODIFY`, `REJECT`).

## 2. API Data Contracts
Input dataclasses (`IncidentDemandInput`, `DepotSupplyInput`) decouple solver invocation from database models. Results are returned as structured `AllocationResult` objects containing fine-grained `CommodityAllocationItem` and `UnmetDemandItem` lists.
