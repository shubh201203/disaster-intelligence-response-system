import os
import hashlib

ROOT_DIR = r"C:\Users\shubh\Downloads\DIRS"
MANIFEST_PATH = os.path.join(ROOT_DIR, "DIRS_MILESTONE_2B_OWNER_AUDIT_ROUND7", "SHA256_MANIFEST.txt")

def sha256_file(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    manifest_map = {}
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                manifest_map[parts[1]] = parts[0]

    files_to_check = {
        # Milestone 2B Engine
        "backend/app/recovery/optimization/schemas.py": "01_MILESTONE_2B_SOURCE/schemas.py",
        "backend/app/recovery/optimization/recovery_cpsat_solver.py": "01_MILESTONE_2B_SOURCE/recovery_cpsat_solver.py",
        "backend/app/recovery/optimization/recovery_optimization_orchestrator.py": "01_MILESTONE_2B_SOURCE/recovery_optimization_orchestrator.py",
        "backend/app/recovery/optimization/infeasibility_advisor.py": "01_MILESTONE_2B_SOURCE/infeasibility_advisor.py",
        "backend/app/recovery/optimization/__init__.py": "01_MILESTONE_2B_SOURCE/__init__.py",
        "tests/backend/test_phase6d_cpsat_solver.py": "01_MILESTONE_2B_SOURCE/test_phase6d_cpsat_solver.py",
        "docs/PHASE6D_B_MILESTONE_2B_RSK_M2_07_DECISION_RECORD.md": "01_MILESTONE_2B_SOURCE/PHASE6D_B_MILESTONE_2B_RSK_M2_07_DECISION_RECORD.md",
        # Milestone 1 Pure Math Services
        "backend/app/recovery/services/calendar_cost_service.py": "03_MILESTONE_1_REFERENCE/calendar_cost_service.py",
        "backend/app/recovery/services/cash_flow_solvency_service.py": "03_MILESTONE_1_REFERENCE/cash_flow_solvency_service.py",
        "backend/app/recovery/services/equity_calculation_service.py": "03_MILESTONE_1_REFERENCE/equity_calculation_service.py",
        "backend/app/recovery/services/life_safety_triage_service.py": "03_MILESTONE_1_REFERENCE/life_safety_triage_service.py",
        "backend/app/recovery/services/mcpi_prioritization_service.py": "03_MILESTONE_1_REFERENCE/mcpi_prioritization_service.py",
        "backend/app/recovery/services/project_dependency_service.py": "03_MILESTONE_1_REFERENCE/project_dependency_service.py",
        "backend/app/recovery/services/vulnerability_scoring_service.py": "03_MILESTONE_1_REFERENCE/vulnerability_scoring_service.py",
    }

    all_matched = True
    print("=" * 80)
    print("VERIFYING FROZEN MILESTONE 2B & MILESTONE 1 FILES AGAINST MANIFEST")
    print("=" * 80)
    for repo_rel, manifest_rel in files_to_check.items():
        repo_path = os.path.join(ROOT_DIR, repo_rel)
        if not os.path.exists(repo_path):
            print(f"[MISSING] {repo_rel}")
            all_matched = False
            continue
        current_hash = sha256_file(repo_path)
        expected_hash = manifest_map.get(manifest_rel)
        match = (current_hash == expected_hash)
        if not match:
            all_matched = False
        status = "MATCH" if match else "MISMATCH"
        print(f"[{status}] {repo_rel}")
        print(f"  Current:  {current_hash}")
        print(f"  Expected: {expected_hash}")

    print("=" * 80)
    print(f"OVERALL INTEGRITY: {'PASSED' if all_matched else 'FAILED'}")
    print("=" * 80)

if __name__ == "__main__":
    main()
