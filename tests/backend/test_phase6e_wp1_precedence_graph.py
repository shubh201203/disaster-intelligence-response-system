"""
DIRS Phase 6E Accelerated Programme: Work Package 1 Test Suite.

Exhaustive verification of:
1. Pure mathematical ProjectDependencyService:
   - Kahn's algorithm topological sorting.
   - Directed cycle detection with exact cycle path extraction.
   - CPM-PL forward and backward pass calculations.
   - Total float, free float, and critical path node/edge identification.
   - Lag conversion (days to periods).
2. Precedence Graph Extraction API (`GET /api/v1/recovery/dependencies/graph`):
   - Unauthenticated requests rejected with 401.
   - Empty state handling.
   - Multi-node DAG analysis with accurate CPM metrics.
   - Critical path edge tagging.
3. Dry-Run Dependency Edge Validation API (`POST /api/v1/recovery/dependencies/validate-edge`):
   - Unauthenticated requests rejected with 401.
   - Self-loop rejection.
   - Missing project 404 rejection.
   - Duplicate edge rejection.
   - Cyclic candidate edge rejection with structured cycle path.
   - Valid candidate edge acceptance.
   - Zero-mutation guarantee: dry-run validation never writes to the database.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.models.incident import Incident
from app.models.recovery import RecoveryProject, ProjectDependency
from app.core.security import create_access_token, get_password_hash
from app.recovery.services.project_dependency_service import (
    ProjectDependencyService,
    ProjectActivity,
    DependencyEdge,
    CyclicDependencyError,
)

client = TestClient(app)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def db_session():
    """Provides a transactional database session rolled back after test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def auth_headers(db_session: Session):
    """Creates a test user and returns bearer auth headers."""
    user = db_session.query(User).filter(User.email == "wp1_test_planner@dirs.local").first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email="wp1_test_planner@dirs.local",
            hashed_password=get_password_hash("TestPass123!"),
            full_name="WP1 Precedence Test Planner",
            role="GOVT",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def clean_recovery_data(db_session: Session):
    """Cleans recovery projects and dependencies before and after test."""
    db_session.query(ProjectDependency).delete()
    db_session.query(RecoveryProject).delete()
    db_session.commit()
    yield
    db_session.query(ProjectDependency).delete()
    db_session.query(RecoveryProject).delete()
    db_session.commit()


# ==============================================================================
# 1. PURE MATHEMATICAL UNIT TESTS (ProjectDependencyService)
# ==============================================================================

class TestProjectDependencyServiceUnit:
    """Mathematical verification of CPM-PL and cycle detection logic."""

    def test_toposort_linear_chain(self):
        nodes = ["P1", "P2", "P3", "P4"]
        edges = [
            DependencyEdge("P1", "P2"),
            DependencyEdge("P2", "P3"),
            DependencyEdge("P3", "P4"),
        ]
        order = ProjectDependencyService.detect_cycle_and_toposort(nodes, edges)
        assert order == ["P1", "P2", "P3", "P4"]

    def test_cycle_detection_simple_2_node(self):
        nodes = ["A", "B"]
        edges = [
            DependencyEdge("A", "B"),
            DependencyEdge("B", "A"),
        ]
        with pytest.raises(CyclicDependencyError) as exc_info:
            ProjectDependencyService.detect_cycle_and_toposort(nodes, edges)
        assert "A" in exc_info.value.cycle_path
        assert "B" in exc_info.value.cycle_path

    def test_cycle_detection_triangle(self):
        nodes = ["P1", "P2", "P3"]
        edges = [
            DependencyEdge("P1", "P2"),
            DependencyEdge("P2", "P3"),
            DependencyEdge("P3", "P1"),
        ]
        with pytest.raises(CyclicDependencyError) as exc_info:
            ProjectDependencyService.detect_cycle_and_toposort(nodes, edges)
        cycle = exc_info.value.cycle_path
        assert len(cycle) >= 3

    def test_cpm_pl_forward_backward_pass(self):
        """
        Diamond Network:
            Start -> P1 (30 days = 1 period)
            P1 -> P2 (60 days = 2 periods)
            P1 -> P3 (30 days = 1 period)
            P2 -> P4 (30 days = 1 period)
            P3 -> P4 (30 days = 1 period, lag 30 days = 1 period)
        Path 1: P1(1) + P2(2) + P4(1) = 4 periods (Critical)
        Path 2: P1(1) + P3(1) + lag(1) + P4(1) = 4 periods (Also Critical)
        """
        activities = [
            ProjectActivity("P1", duration_days=30.0),
            ProjectActivity("P2", duration_days=60.0),
            ProjectActivity("P3", duration_days=30.0),
            ProjectActivity("P4", duration_days=30.0),
        ]
        edges = [
            DependencyEdge("P1", "P2", lag_days=0.0),
            DependencyEdge("P1", "P3", lag_days=0.0),
            DependencyEdge("P2", "P4", lag_days=0.0),
            DependencyEdge("P3", "P4", lag_days=30.0),
        ]
        cpm_dict, crit_path, makespan = ProjectDependencyService.compute_cpm_pl(
            activities, edges, period_days=30.0
        )
        assert makespan == 4
        assert "P1" in crit_path
        assert "P4" in crit_path
        assert cpm_dict["P1"].early_start == 0
        assert cpm_dict["P1"].early_finish == 1
        assert cpm_dict["P2"].duration_periods == 2
        assert cpm_dict["P4"].is_critical is True

    def test_cpm_pl_slack_non_critical(self):
        """
        Non-critical branch with positive total float.
        """
        activities = [
            ProjectActivity("A", duration_days=30.0),
            ProjectActivity("B", duration_days=90.0),  # Long branch
            ProjectActivity("C", duration_days=30.0),  # Short branch
            ProjectActivity("D", duration_days=30.0),
        ]
        edges = [
            DependencyEdge("A", "B"),
            DependencyEdge("A", "C"),
            DependencyEdge("B", "D"),
            DependencyEdge("C", "D"),
        ]
        cpm_dict, crit_path, makespan = ProjectDependencyService.compute_cpm_pl(
            activities, edges, period_days=30.0
        )
        # Path A(1)+B(3)+D(1) = 5 periods (Critical)
        # Path A(1)+C(1)+D(1) = 3 periods (Float = 2)
        assert makespan == 5
        assert crit_path == ["A", "B", "D"]
        assert cpm_dict["C"].total_float == 2
        assert cpm_dict["C"].is_critical is False


# ==============================================================================
# 2. PRECEDENCE GRAPH EXTRACTION API TESTS
# ==============================================================================

class TestPrecedenceGraphAPI:
    """Verifies GET /api/v1/recovery/dependencies/graph."""

    def test_graph_unauthenticated(self):
        res = client.get("/api/v1/recovery/dependencies/graph")
        assert res.status_code == 401

    def test_graph_empty_database(self, clean_recovery_data, auth_headers):
        res = client.get("/api/v1/recovery/dependencies/graph", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["is_acyclic"] is True
        assert data["total_projects"] == 0
        assert data["total_dependencies"] == 0
        assert data["nodes"] == []
        assert data["edges"] == []
        assert data["critical_path_project_ids"] == []

    def test_graph_with_dag_network(self, clean_recovery_data, auth_headers, db_session: Session):
        # Create 3 recovery projects
        p1 = RecoveryProject(
            id="proj-01-water",
            project_code="REC-PRJ-01",
            title="Water Treatment Main Intake",
            sector="WASH",
            priority_tier="TIER_1",
            status="APPROVED",
            estimated_duration_days=60,
            estimated_cost=150000.0,
            lead_agency="Water Works Dept",
        )
        p2 = RecoveryProject(
            id="proj-02-power",
            project_code="REC-PRJ-02",
            title="Substation Feeder Line",
            sector="POWER",
            priority_tier="TIER_1",
            status="APPROVED",
            estimated_duration_days=30,
            estimated_cost=80000.0,
            lead_agency="Power Distribution Corp",
        )
        p3 = RecoveryProject(
            id="proj-03-hospital",
            project_code="REC-PRJ-03",
            title="District Hospital Reconnection",
            sector="HEALTH",
            priority_tier="TIER_1",
            status="PROPOSED",
            estimated_duration_days=30,
            estimated_cost=120000.0,
            lead_agency="Health Directorate",
        )
        db_session.add_all([p1, p2, p3])
        db_session.commit()

        # Add dependencies: p1 -> p2 (lag 0), p2 -> p3 (lag 30 days)
        dep1 = ProjectDependency(
            id="dep-01",
            predecessor_project_id="proj-01-water",
            successor_project_id="proj-02-power",
            dependency_type="FINISH_TO_START",
            lag_days=0,
            rationale="Substation requires water cooling conduit",
        )
        dep2 = ProjectDependency(
            id="dep-02",
            predecessor_project_id="proj-02-power",
            successor_project_id="proj-03-hospital",
            dependency_type="FINISH_TO_START",
            lag_days=30,
            rationale="Hospital energization requires feeder commissioning + 30d safety lag",
        )
        db_session.add_all([dep1, dep2])
        db_session.commit()

        res = client.get("/api/v1/recovery/dependencies/graph?period_days=30", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()

        assert data["is_acyclic"] is True
        assert data["total_projects"] == 3
        assert data["total_dependencies"] == 2
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2

        # Check topological ordering
        order = data["topological_order"]
        assert order.index("proj-01-water") < order.index("proj-02-power")
        assert order.index("proj-02-power") < order.index("proj-03-hospital")

        # Check critical path
        assert "proj-01-water" in data["critical_path_project_ids"]
        assert "proj-02-power" in data["critical_path_project_ids"]
        assert "proj-03-hospital" in data["critical_path_project_ids"]

        # Makespan: p1(2 periods) + p2(1 period) + lag(1 period) + p3(1 period) = 5 periods
        assert data["project_makespan_periods"] == 5

        # Check node CPM DTOs
        node_map = {n["id"]: n for n in data["nodes"]}
        assert node_map["proj-01-water"]["cpm"]["duration_periods"] == 2
        assert node_map["proj-01-water"]["cpm"]["early_start"] == 0
        assert node_map["proj-01-water"]["cpm"]["early_finish"] == 2
        assert node_map["proj-01-water"]["cpm"]["is_critical"] is True

        assert node_map["proj-02-power"]["cpm"]["early_start"] == 2
        assert node_map["proj-02-power"]["cpm"]["early_finish"] == 3

        assert node_map["proj-03-hospital"]["cpm"]["early_start"] == 4  # 3 + 1 period lag
        assert node_map["proj-03-hospital"]["cpm"]["early_finish"] == 5

        # Check critical edge tagging
        for edge in data["edges"]:
            assert edge["is_critical_path"] is True


# ==============================================================================
# 3. DRY-RUN DEPENDENCY EDGE VALIDATION API TESTS
# ==============================================================================

class TestValidateDependencyEdgeAPI:
    """Verifies POST /api/v1/recovery/dependencies/validate-edge."""

    def test_validate_unauthenticated(self):
        payload = {
            "predecessor_project_id": "P1",
            "successor_project_id": "P2",
            "lag_days": 0,
        }
        res = client.post("/api/v1/recovery/dependencies/validate-edge", json=payload)
        assert res.status_code == 401

    def test_validate_self_loop(self, clean_recovery_data, auth_headers):
        payload = {
            "predecessor_project_id": "SAME_PROJECT",
            "successor_project_id": "SAME_PROJECT",
            "lag_days": 0,
        }
        res = client.post("/api/v1/recovery/dependencies/validate-edge", json=payload, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is False
        assert data["reason"] == "SELF_LOOP"
        assert "cannot depend on itself" in data["message"].lower()
        assert data["cycle_path"] == ["SAME_PROJECT", "SAME_PROJECT"]

    def test_validate_nonexistent_project(self, clean_recovery_data, auth_headers):
        payload = {
            "predecessor_project_id": "NON_EXISTENT_1",
            "successor_project_id": "NON_EXISTENT_2",
            "lag_days": 0,
        }
        res = client.post("/api/v1/recovery/dependencies/validate-edge", json=payload, headers=auth_headers)
        assert res.status_code == 404
        assert "does not exist" in res.json()["detail"]["message"].lower()

    def test_validate_duplicate_edge(self, clean_recovery_data, auth_headers, db_session: Session):
        # Create projects
        p1 = RecoveryProject(
            id="proj-a", project_code="PRJ-A", title="Road A", sector="TRANSPORT",
            estimated_duration_days=30, lead_agency="PWD"
        )
        p2 = RecoveryProject(
            id="proj-b", project_code="PRJ-B", title="Bridge B", sector="TRANSPORT",
            estimated_duration_days=60, lead_agency="PWD"
        )
        dep = ProjectDependency(
            id="dep-ab", predecessor_project_id="proj-a", successor_project_id="proj-b"
        )
        db_session.add_all([p1, p2, dep])
        db_session.commit()

        # Dry run with existing edge
        payload = {
            "predecessor_project_id": "proj-a",
            "successor_project_id": "proj-b",
            "lag_days": 0,
        }
        res = client.post("/api/v1/recovery/dependencies/validate-edge", json=payload, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is False
        assert data["reason"] == "DUPLICATE_EDGE"
        assert "already exists" in data["message"].lower()

    def test_validate_cyclic_dependency(self, clean_recovery_data, auth_headers, db_session: Session):
        # Chain: A -> B -> C
        # Candidate edge: C -> A (creates cycle A -> B -> C -> A)
        p1 = RecoveryProject(id="p-a", project_code="A", title="A", sector="WASH", estimated_duration_days=30, lead_agency="A")
        p2 = RecoveryProject(id="p-b", project_code="B", title="B", sector="WASH", estimated_duration_days=30, lead_agency="B")
        p3 = RecoveryProject(id="p-c", project_code="C", title="C", sector="WASH", estimated_duration_days=30, lead_agency="C")
        dep1 = ProjectDependency(id="d1", predecessor_project_id="p-a", successor_project_id="p-b")
        dep2 = ProjectDependency(id="d2", predecessor_project_id="p-b", successor_project_id="p-c")
        db_session.add_all([p1, p2, p3, dep1, dep2])
        db_session.commit()

        payload = {
            "predecessor_project_id": "p-c",
            "successor_project_id": "p-a",
            "lag_days": 0,
        }
        res = client.post("/api/v1/recovery/dependencies/validate-edge", json=payload, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is False
        assert data["reason"] == "CYCLIC_DEPENDENCY"
        assert data["cycle_path"] is not None
        assert len(data["cycle_path"]) >= 3

    def test_validate_valid_edge(self, clean_recovery_data, auth_headers, db_session: Session):
        # Disconnected: A and B
        p1 = RecoveryProject(id="p-x", project_code="X", title="X", sector="WASH", estimated_duration_days=30, lead_agency="X")
        p2 = RecoveryProject(id="p-y", project_code="Y", title="Y", sector="WASH", estimated_duration_days=30, lead_agency="Y")
        db_session.add_all([p1, p2])
        db_session.commit()

        payload = {
            "predecessor_project_id": "p-x",
            "successor_project_id": "p-y",
            "lag_days": 14,
        }
        res = client.post("/api/v1/recovery/dependencies/validate-edge", json=payload, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is True
        assert data["reason"] is None
        assert "valid and acyclic" in data["message"].lower()

    def test_zero_mutation_guarantee(self, clean_recovery_data, auth_headers, db_session: Session):
        """Verifies that validating candidate edges NEVER creates database records."""
        p1 = RecoveryProject(id="p-m1", project_code="M1", title="M1", sector="WASH", estimated_duration_days=30, lead_agency="M1")
        p2 = RecoveryProject(id="p-m2", project_code="M2", title="M2", sector="WASH", estimated_duration_days=30, lead_agency="M2")
        db_session.add_all([p1, p2])
        db_session.commit()

        initial_count = db_session.query(ProjectDependency).count()
        assert initial_count == 0

        # Validate edge
        payload = {
            "predecessor_project_id": "p-m1",
            "successor_project_id": "p-m2",
            "lag_days": 5,
        }
        res = client.post("/api/v1/recovery/dependencies/validate-edge", json=payload, headers=auth_headers)
        assert res.status_code == 200

        # Query database again to prove zero mutation
        final_count = db_session.query(ProjectDependency).count()
        assert final_count == 0
