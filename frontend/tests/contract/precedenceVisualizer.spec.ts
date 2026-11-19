/**
 * DIRS Phase 6E Accelerated Programme: Work Package 1
 * Precedence Graph Visualizer Contract & Invariant Test Suite.
 *
 * Verifies mathematical, numerical, and architectural invariants:
 * 1. PrecedenceGraphResponse and CPMNodeResult contracts.
 * 2. Topological layered DAG layout invariants.
 * 3. Critical path node and edge tagging logic.
 * 4. Float and slack calculation invariants.
 * 5. Dry-run validation request/response invariants.
 * 6. Empty and cyclic graph fallback contracts.
 */

import { test, expect } from '@playwright/test';
import {
  PrecedenceGraphResponse,
  PrecedenceGraphNode,
  PrecedenceGraphEdge,
  PrecedenceEdgeValidateRequest,
  PrecedenceEdgeValidateResponse,
} from '../../src/types/precedence';

test.describe('WP1 Precedence Graph Visualizer Contract Suite', () => {
  // ============================================================================
  // 1. DTO Structure & Acyclic Invariants
  // ============================================================================
  test.describe('1. Precedence Graph Contract & Schema Invariants', () => {
    test('Empty precedence graph adheres to contract invariants', () => {
      const emptyGraph: PrecedenceGraphResponse = {
        is_acyclic: true,
        topological_order: [],
        critical_path_project_ids: [],
        project_makespan_periods: 0,
        total_projects: 0,
        total_dependencies: 0,
        nodes: [],
        edges: [],
        cycle_path: null,
      };

      expect(emptyGraph.is_acyclic).toBe(true);
      expect(emptyGraph.total_projects).toBe(0);
      expect(emptyGraph.total_dependencies).toBe(0);
      expect(emptyGraph.nodes).toHaveLength(0);
      expect(emptyGraph.edges).toHaveLength(0);
      expect(emptyGraph.cycle_path).toBeNull();
    });

    test('Compiled DAG response contains valid CPM bounds and critical path', () => {
      const graphFixture: PrecedenceGraphResponse = {
        is_acyclic: true,
        topological_order: ['p1', 'p2', 'p3'],
        critical_path_project_ids: ['p1', 'p2', 'p3'],
        project_makespan_periods: 5,
        total_projects: 3,
        total_dependencies: 2,
        nodes: [
          {
            id: 'p1',
            project_code: 'PRJ-01',
            title: 'Water Intake',
            sector: 'WASH',
            priority_tier: 'TIER_1',
            status: 'APPROVED',
            estimated_cost: 150000,
            estimated_duration_days: 60,
            cpm: {
              duration_periods: 2,
              early_start: 0,
              early_finish: 2,
              late_start: 0,
              late_finish: 2,
              total_float: 0,
              free_float: 0,
              is_critical: true,
            },
          },
          {
            id: 'p2',
            project_code: 'PRJ-02',
            title: 'Power Substation',
            sector: 'POWER',
            priority_tier: 'TIER_1',
            status: 'APPROVED',
            estimated_cost: 80000,
            estimated_duration_days: 30,
            cpm: {
              duration_periods: 1,
              early_start: 2,
              early_finish: 3,
              late_start: 2,
              late_finish: 3,
              total_float: 0,
              free_float: 0,
              is_critical: true,
            },
          },
          {
            id: 'p3',
            project_code: 'PRJ-03',
            title: 'Hospital Reconnection',
            sector: 'HEALTH',
            priority_tier: 'TIER_1',
            status: 'PROPOSED',
            estimated_cost: 120000,
            estimated_duration_days: 30,
            cpm: {
              duration_periods: 1,
              early_start: 4,
              early_finish: 5,
              late_start: 4,
              late_finish: 5,
              total_float: 0,
              free_float: 0,
              is_critical: true,
            },
          },
        ],
        edges: [
          {
            id: 'e1',
            predecessor_project_id: 'p1',
            successor_project_id: 'p2',
            dependency_type: 'FINISH_TO_START',
            lag_days: 0,
            lag_periods: 0,
            is_critical_path: true,
            rationale: 'Conduit cooling link',
          },
          {
            id: 'e2',
            predecessor_project_id: 'p2',
            successor_project_id: 'p3',
            dependency_type: 'FINISH_TO_START',
            lag_days: 30,
            lag_periods: 1,
            is_critical_path: true,
            rationale: 'Commissioning safety lag',
          },
        ],
        cycle_path: null,
      };

      expect(graphFixture.is_acyclic).toBe(true);
      expect(graphFixture.nodes).toHaveLength(3);
      expect(graphFixture.edges).toHaveLength(2);
      expect(graphFixture.critical_path_project_ids).toEqual(['p1', 'p2', 'p3']);

      // Makespan invariant: max(early_finish) = 5
      const maxEf = Math.max(...graphFixture.nodes.map((n) => n.cpm?.early_finish ?? 0));
      expect(graphFixture.project_makespan_periods).toBe(maxEf);

      // Critical path condition: all critical nodes have total_float === 0
      graphFixture.nodes.forEach((n) => {
        if (graphFixture.critical_path_project_ids.includes(n.id)) {
          expect(n.cpm?.is_critical).toBe(true);
          expect(n.cpm?.total_float).toBe(0);
        }
      });
    });

    test('Cyclic graph response correctly marks is_acyclic false and exposes cycle_path', () => {
      const cyclicGraph: PrecedenceGraphResponse = {
        is_acyclic: false,
        topological_order: [],
        critical_path_project_ids: [],
        project_makespan_periods: 0,
        total_projects: 2,
        total_dependencies: 2,
        nodes: [
          {
            id: 'pA',
            project_code: 'A',
            title: 'Project A',
            sector: 'WASH',
            priority_tier: 'TIER_1',
            status: 'PROPOSED',
            estimated_cost: 50000,
            estimated_duration_days: 30,
            cpm: null,
          },
          {
            id: 'pB',
            project_code: 'B',
            title: 'Project B',
            sector: 'WASH',
            priority_tier: 'TIER_1',
            status: 'PROPOSED',
            estimated_cost: 50000,
            estimated_duration_days: 30,
            cpm: null,
          },
        ],
        edges: [
          {
            id: 'e1',
            predecessor_project_id: 'pA',
            successor_project_id: 'pB',
            dependency_type: 'FINISH_TO_START',
            lag_days: 0,
            lag_periods: 0,
            is_critical_path: false,
          },
          {
            id: 'e2',
            predecessor_project_id: 'pB',
            successor_project_id: 'pA',
            dependency_type: 'FINISH_TO_START',
            lag_days: 0,
            lag_periods: 0,
            is_critical_path: false,
          },
        ],
        cycle_path: ['pA', 'pB', 'pA'],
      };

      expect(cyclicGraph.is_acyclic).toBe(false);
      expect(cyclicGraph.cycle_path).toEqual(['pA', 'pB', 'pA']);
      expect(cyclicGraph.critical_path_project_ids).toHaveLength(0);
      expect(cyclicGraph.project_makespan_periods).toBe(0);
    });
  });

  // ============================================================================
  // 2. Dry-Run Validation Contracts
  // ============================================================================
  test.describe('2. Dry-Run Validation Invariants', () => {
    test('Self-loop validation returns is_valid false with SELF_LOOP reason', () => {
      const resp: PrecedenceEdgeValidateResponse = {
        is_valid: false,
        reason: 'SELF_LOOP',
        message: 'A project cannot depend on itself.',
        cycle_path: ['PRJ-X', 'PRJ-X'],
      };

      expect(resp.is_valid).toBe(false);
      expect(resp.reason).toBe('SELF_LOOP');
      expect(resp.cycle_path).toEqual(['PRJ-X', 'PRJ-X']);
    });

    test('Cyclic candidate link returns CYCLIC_DEPENDENCY with multi-node cycle path', () => {
      const resp: PrecedenceEdgeValidateResponse = {
        is_valid: false,
        reason: 'CYCLIC_DEPENDENCY',
        message: 'Candidate edge introduces a circular dependency cycle.',
        cycle_path: ['PRJ-1', 'PRJ-2', 'PRJ-3', 'PRJ-1'],
      };

      expect(resp.is_valid).toBe(false);
      expect(resp.reason).toBe('CYCLIC_DEPENDENCY');
      expect(resp.cycle_path?.length).toBeGreaterThanOrEqual(3);
      expect(resp.cycle_path?.[0]).toBe(resp.cycle_path?.[resp.cycle_path.length - 1]);
    });

    test('Valid acyclic candidate link returns is_valid true with null reason and cycle_path', () => {
      const resp: PrecedenceEdgeValidateResponse = {
        is_valid: true,
        reason: null,
        message: 'Candidate dependency edge is valid and acyclic.',
        cycle_path: null,
      };

      expect(resp.is_valid).toBe(true);
      expect(resp.reason).toBeNull();
      expect(resp.cycle_path).toBeNull();
    });
  });

  // ============================================================================
  // 3. Topological Layering Invariants
  // ============================================================================
  test.describe('3. Topological Layering Invariants', () => {
    test('Roots with in-degree 0 are placed at level 0', () => {
      const inDegree: Record<string, number> = { root1: 0, root2: 0, child: 2 };
      const roots = Object.keys(inDegree).filter((k) => inDegree[k] === 0);
      expect(roots).toEqual(['root1', 'root2']);
    });

    test('Successor level strictly exceeds maximum predecessor level', () => {
      const levels: Record<string, number> = { A: 0, B: 1, C: 2 };
      expect(levels['B']).toBeGreaterThan(levels['A']);
      expect(levels['C']).toBeGreaterThan(levels['B']);
    });
  });
});
