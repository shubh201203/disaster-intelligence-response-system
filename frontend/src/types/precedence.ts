/**
 * DIRS Phase 6E Accelerated Programme: Work Package 1
 * Precedence Graph and Dependency Types.
 */

export interface PrecedenceCPMInfo {
  duration_periods: number;
  early_start: number;
  early_finish: number;
  late_start: number;
  late_finish: number;
  total_float: number;
  free_float: number;
  is_critical: boolean;
}

export interface PrecedenceGraphNode {
  id: string;
  project_code: string;
  title: string;
  sector: string;
  priority_tier: string;
  status: string;
  estimated_cost: number;
  estimated_duration_days: number;
  cpm?: PrecedenceCPMInfo | null;
}

export interface PrecedenceGraphEdge {
  id: string;
  predecessor_project_id: string;
  successor_project_id: string;
  dependency_type: string;
  lag_days: number;
  lag_periods: number;
  is_critical_path: boolean;
  rationale?: string | null;
}

export interface PrecedenceGraphResponse {
  is_acyclic: boolean;
  topological_order: string[];
  critical_path_project_ids: string[];
  project_makespan_periods: number;
  total_projects: number;
  total_dependencies: number;
  nodes: PrecedenceGraphNode[];
  edges: PrecedenceGraphEdge[];
  cycle_path?: string[] | null;
}

export interface PrecedenceEdgeValidateRequest {
  predecessor_project_id: string;
  successor_project_id: string;
  lag_days?: number;
  dependency_type?: string;
}

export interface PrecedenceEdgeValidateResponse {
  is_valid: boolean;
  reason?: string | null;
  message: string;
  cycle_path?: string[] | null;
}
