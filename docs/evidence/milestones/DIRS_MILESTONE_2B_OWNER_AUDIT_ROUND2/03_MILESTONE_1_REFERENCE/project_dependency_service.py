"""
Project Dependency Pure Mathematical Service.

Phase 6D-B Milestone 1 Domain Implementation.
Provides Directed Acyclic Graph (DAG) analysis and Critical Path Method with
Positive Lag (CPM-PL) for recovery infrastructure project sequencing:
- Kahn's algorithm topological sorting.
- Cycle detection with exact directed cycle path extraction.
- Transitive cascade (downstream reachability closure) calculation.
- Critical Path Method with Positive Lag (CPM-PL) forward/backward pass.
- Discrete period lag conversion with ceil rounding: ceil(L_days / delta_t).

Pure mathematical logic: independent of database persistence and API routes.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Set, Tuple


class CyclicDependencyError(ValueError):
    """Raised when a circular dependency cycle is detected in the project graph."""
    def __init__(self, cycle_path: List[str]):
        self.cycle_path = cycle_path
        super().__init__(f"Circular dependency cycle detected: {' -> '.join(cycle_path)}")


@dataclass
class DependencyEdge:
    """Directed precedence dependency: predecessor -> successor."""
    predecessor_id: str
    successor_id: str
    lag_days: float = 0.0          # Positive calendar lag in days
    lag_periods: Optional[int] = None # Discrete period lag (computed if None)


@dataclass
class ProjectActivity:
    """Project node in the dependency network."""
    project_id: str
    duration_days: float = 0.0
    duration_periods: Optional[int] = None


@dataclass
class CPMNodeResult:
    """CPM schedule metrics for a single project activity."""
    project_id: str
    duration_periods: int
    early_start: int
    early_finish: int
    late_start: int
    late_finish: int
    total_float: int
    free_float: int
    is_critical: bool


@dataclass
class DAGAnalysisResult:
    """Comprehensive DAG analysis result."""
    is_acyclic: bool
    topological_order: List[str]
    transitive_cascade_counts: Dict[str, int]
    cpm_results: Dict[str, CPMNodeResult]
    critical_path: List[str]
    project_makespan_periods: int


class ProjectDependencyService:
    """
    Pure mathematical engine for precedence DAG and CPM-PL schedule analysis.
    """
    DEFAULT_PERIOD_DAYS: float = 30.0

    @classmethod
    def convert_days_to_periods(cls, days: float, period_days: Optional[float] = None, is_duration: bool = False) -> int:
        """
        Converts calendar days to discrete periods:
        lag_periods = ceil(lag_days / delta_t)
        duration_periods = max(1, ceil(d_days / delta_t)) if d_days > 0 else 0
        """
        delta_t = period_days if period_days is not None else cls.DEFAULT_PERIOD_DAYS
        if delta_t <= 0.0:
            raise ValueError(f"Period duration in days must be positive, got {delta_t}")
        if days < 0.0:
            raise ValueError(f"Days cannot be negative, got {days}")

        if days == 0.0:
            return 0
        
        periods = int(math.ceil(days / delta_t))
        if is_duration:
            return max(1, periods)
        return periods

    @classmethod
    def detect_cycle_and_toposort(
        cls,
        nodes: List[str],
        edges: List[DependencyEdge],
    ) -> List[str]:
        """
        Kahn's algorithm with cycle path extraction.
        Returns topological ordering if acyclic; raises CyclicDependencyError with cycle path if cyclic.
        """
        in_degree: Dict[str, int] = {node: 0 for node in nodes}
        adj_list: Dict[str, List[str]] = {node: [] for node in nodes}

        for edge in edges:
            if edge.predecessor_id not in in_degree:
                in_degree[edge.predecessor_id] = 0
                adj_list[edge.predecessor_id] = []
            if edge.successor_id not in in_degree:
                in_degree[edge.successor_id] = 0
                adj_list[edge.successor_id] = []

            adj_list[edge.predecessor_id].append(edge.successor_id)
            in_degree[edge.successor_id] += 1

        queue = deque([node for node, deg in in_degree.items() if deg == 0])
        topological_order: List[str] = []

        while queue:
            u = queue.popleft()
            topological_order.append(u)
            for v in adj_list[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        if len(topological_order) != len(in_degree):
            # Graph has cycle. Find exact cycle path using DFS.
            cycle = cls._extract_cycle_path(adj_list, in_degree)
            raise CyclicDependencyError(cycle)

        return topological_order

    @classmethod
    def _extract_cycle_path(cls, adj_list: Dict[str, List[str]], in_degree: Dict[str, int]) -> List[str]:
        """Extracts an ordered directed cycle from remaining non-zero in-degree vertices."""
        visited: Dict[str, int] = {} # 0: unvisited, 1: visiting (in stack), 2: visited
        parent: Dict[str, str] = {}
        cycle_nodes: List[str] = []

        def dfs(u: str) -> bool:
            visited[u] = 1
            for v in adj_list.get(u, []):
                if visited.get(v, 0) == 1:
                    # Found cycle: reconstruct path from v to u, then append v
                    curr = u
                    cycle_nodes.append(v)
                    while curr != v:
                        cycle_nodes.append(curr)
                        curr = parent.get(curr, v)
                    cycle_nodes.append(v)
                    cycle_nodes.reverse()
                    return True
                elif visited.get(v, 0) == 0:
                    parent[v] = u
                    if dfs(v):
                        return True
            visited[u] = 2
            return False

        for node in in_degree:
            if in_degree[node] > 0 and visited.get(node, 0) == 0:
                if dfs(node):
                    return cycle_nodes

        # Fallback if no specific node caught
        return ["UNKNOWN_CYCLE"]

    @classmethod
    def calculate_transitive_cascades(
        cls,
        nodes: List[str],
        edges: List[DependencyEdge],
    ) -> Dict[str, int]:
        """
        Calculates transitive cascade reachability:
        count of all downstream reachable project vertices from node u.
        """
        adj_list: Dict[str, List[str]] = {node: [] for node in nodes}
        for edge in edges:
            adj_list[edge.predecessor_id].append(edge.successor_id)

        cascade_counts: Dict[str, int] = {}

        for u in nodes:
            visited: Set[str] = set()
            queue = deque([u])
            while queue:
                curr = queue.popleft()
                for neighbor in adj_list.get(curr, []):
                    if neighbor not in visited and neighbor != u:
                        visited.add(neighbor)
                        queue.append(neighbor)
            cascade_counts[u] = len(visited)

        return cascade_counts

    @classmethod
    def compute_cpm_pl(
        cls,
        activities: List[ProjectActivity],
        edges: List[DependencyEdge],
        period_days: Optional[float] = None,
    ) -> Tuple[Dict[str, CPMNodeResult], List[str], int]:
        """
        Executes Critical Path Method with Positive Lag (CPM-PL):
        - Forward pass: ES, EF
        - Backward pass: LF, LS
        - Total Float (TF) and Free Float (FF)
        - Critical path identification (TF == 0)
        """
        delta_t = period_days if period_days is not None else cls.DEFAULT_PERIOD_DAYS
        node_ids = [act.project_id for act in activities]
        toposort = cls.detect_cycle_and_toposort(node_ids, edges)

        # Durations in periods
        durations: Dict[str, int] = {}
        for act in activities:
            if act.duration_periods is not None:
                durations[act.project_id] = act.duration_periods
            else:
                durations[act.project_id] = cls.convert_days_to_periods(act.duration_days, delta_t, is_duration=True)

        # Build adjacency with lags in discrete periods
        pred_map: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        succ_map: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

        for edge in edges:
            if edge.lag_periods is not None:
                lag = edge.lag_periods
            else:
                lag = cls.convert_days_to_periods(edge.lag_days, delta_t, is_duration=False)
            pred_map[edge.successor_id].append((edge.predecessor_id, lag))
            succ_map[edge.predecessor_id].append((edge.successor_id, lag))

        # Forward Pass
        es: Dict[str, int] = {}
        ef: Dict[str, int] = {}

        for u in toposort:
            if not pred_map[u]:
                es[u] = 0
            else:
                es[u] = max(ef[p] + lag for p, lag in pred_map[u])
            ef[u] = es[u] + durations[u]

        makespan = max(ef.values()) if ef else 0

        # Backward Pass
        lf: Dict[str, int] = {}
        ls: Dict[str, int] = {}

        for u in reversed(toposort):
            if not succ_map[u]:
                lf[u] = makespan
            else:
                lf[u] = min(ls[s] - lag for s, lag in succ_map[u])
            ls[u] = lf[u] - durations[u]

        # Floats and Critical Path
        cpm_results: Dict[str, CPMNodeResult] = {}
        critical_path: List[str] = []

        for u in toposort:
            tf = ls[u] - es[u]
            if not succ_map[u]:
                ff = makespan - ef[u]
            else:
                ff = min(es[s] - lag for s, lag in succ_map[u]) - ef[u]
            
            is_crit = (tf == 0)
            if is_crit:
                critical_path.append(u)

            cpm_results[u] = CPMNodeResult(
                project_id=u,
                duration_periods=durations[u],
                early_start=es[u],
                early_finish=ef[u],
                late_start=ls[u],
                late_finish=lf[u],
                total_float=tf,
                free_float=max(0, ff),
                is_critical=is_crit,
            )

        return cpm_results, critical_path, makespan

    @classmethod
    def analyze_network(
        cls,
        activities: List[ProjectActivity],
        edges: List[DependencyEdge],
        period_days: Optional[float] = None,
    ) -> DAGAnalysisResult:
        """Full network analysis pipeline."""
        node_ids = [act.project_id for act in activities]
        toposort = cls.detect_cycle_and_toposort(node_ids, edges)
        cascades = cls.calculate_transitive_cascades(node_ids, edges)
        cpm_res, crit_path, makespan = cls.compute_cpm_pl(activities, edges, period_days)

        return DAGAnalysisResult(
            is_acyclic=True,
            topological_order=toposort,
            transitive_cascade_counts=cascades,
            cpm_results=cpm_res,
            critical_path=crit_path,
            project_makespan_periods=makespan,
        )
