import uuid, json
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.incident import Incident
from app.models.resource import Resource
from app.models.rescue import RescueTask

client = TestClient(app)

def create_user(role):
    email = f"{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": f"{role} Closure Auditor",
        "role": role
    })
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"}).json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}

print("=== 1. CREATING AUDIT TOKENS ===")
c_tok, c_hdr = create_user("CITIZEN")
g_tok, g_hdr = create_user("GOVT")
v_tok, v_hdr = create_user("VOLUNTEER")
n_tok, n_hdr = create_user("NGO")
print("Tokens created successfully.")

print("\n=== 2. CITIZEN SOS WITH GPS ===")
r_sos_gps = client.post("/api/v1/incidents/sos?lat=13.0827&lng=80.2707&description=Citizen%20trapped%20in%20flood", headers=c_hdr)
print("SOS GPS status:", r_sos_gps.status_code, "Code:", r_sos_gps.json().get("incident_code"), "Priority:", r_sos_gps.json().get("priority_score"))
inc_gps_id = r_sos_gps.json().get("id")

print("\n=== 3. CITIZEN SOS WITHOUT GPS ===")
r_sos_nogps = client.post("/api/v1/incidents/sos?location_address=Tower%20Block%20B%2C%20Ward%204&description=Medical%20emergency%20no%20gps", headers=c_hdr)
print("SOS No-GPS status:", r_sos_nogps.status_code, "Address:", r_sos_nogps.json().get("location_address"), "Lat:", r_sos_nogps.json().get("latitude"), "Priority:", r_sos_nogps.json().get("priority_score"))

print("\n=== 4. CITIZEN INCIDENT REPORT ===")
r_rep = client.post("/api/v1/incidents", headers=c_hdr, json={
    "title": "Chemical Factory Vapor Leak",
    "disaster_type": "FIRE",
    "description": "Dense smoke and chemical odor observed near industrial park",
    "latitude": 13.0900,
    "longitude": 80.2800,
    "location_address": "Sector 9 Industrial Corridor",
    "people_affected": 45,
    "severity": "HIGH"
})
print("Report status:", r_rep.status_code, "Code:", r_rep.json().get("incident_code"), "Status:", r_rep.json().get("status"))

print("\n=== 5. CITIZEN SHELTER SEARCH ===")
r_sh = client.get("/api/v1/shelters/nearby?lat=13.0827&lng=80.2707&radius_km=25")
print("Shelters nearby status:", r_sh.status_code, "Count:", len(r_sh.json()))
if r_sh.json():
    s0 = r_sh.json()[0]
    print("  Top Shelter:", s0.get("name"), "Distance:", s0.get("distance_km"), "Coords:", s0.get("latitude"), s0.get("longitude"))

print("\n=== 6. GROUNDED SAFETY ASSISTANT (ALL 7 HAZARDS) ===")
hazards = [
    ("FLOOD", "What should I do during rising floodwaters?"),
    ("CYCLONE", "How to prepare for cyclone storm surge?"),
    ("FIRE", "What is the evacuation procedure for a structural fire?"),
    ("EARTHQUAKE", "What are safety rules during earthquake tremors?"),
    ("LANDSLIDE", "What are landslide early warning signs and slope evacuation rules?"),
    ("TSUNAMI", "What is the immediate action upon receiving a coastal tsunami warning?"),
    ("INDUSTRIAL_CHEMICAL", "What precautions are required during a toxic chemical gas release?")
]
for h_type, q in hazards:
    r_ai = client.post("/api/v1/ai/rag/query", headers=c_hdr, json={"query": q, "mode": "GENERAL_COPILOT"})
    d = r_ai.json()
    print(f"  {h_type}: Grounded={d.get('is_grounded')} Conf={d.get('confidence')} Citations={len(d.get('citations', []))} Summary={d.get('summary')[:75]}...")

print("\n=== 7. GOVERNMENT COMMAND CENTER VISIBILITY ===")
r_gov_inc = client.get("/api/v1/incidents", headers=g_hdr)
print("Govt incident list status:", r_gov_inc.status_code, "Total incidents:", len(r_gov_inc.json()))
found_sos = any(i["id"] == inc_gps_id for i in r_gov_inc.json())
print("Govt visibility of SOS incident:", found_sos)

print("\n=== 8. GOVERNMENT VOLUNTEER ASSIGNMENT ===")
vol_user_res = client.get("/api/v1/volunteers/me", headers=v_hdr)
vol_id = vol_user_res.json()["id"]
r_assign = client.post(f"/api/v1/volunteers/assign?incident_id={inc_gps_id}&volunteer_id={vol_id}", headers=g_hdr)
print("Govt task assignment status:", r_assign.status_code, "Task ID:", r_assign.json().get("task_id"))
task_id = r_assign.json().get("task_id")

print("\n=== 9. VOLUNTEER MY-TASKS & ACCEPTANCE ===")
r_my_tasks = client.get("/api/v1/volunteers/my-tasks", headers=v_hdr)
print("Volunteer my-tasks count:", len(r_my_tasks.json()))
t0 = r_my_tasks.json()[0]
print("  Task initial status:", t0.get("status"), "Incident:", t0.get("incident_code"), "Coords:", t0.get("latitude"), t0.get("longitude"))

r_accept = client.post(f"/api/v1/volunteers/tasks/{task_id}/status?target_status=ACCEPTED", headers=v_hdr)
print("Volunteer acceptance status:", r_accept.status_code, "New task status:", r_accept.json().get("status"))

r_my_tasks_refreshed = client.get("/api/v1/volunteers/my-tasks", headers=v_hdr)
print("Volunteer refreshed task status:", r_my_tasks_refreshed.json()[0].get("status"))

print("\n=== 10. GOVT VISIBILITY OF VOLUNTEER ACCEPTANCE ===")
r_all_tasks = client.get("/api/v1/volunteers/tasks", headers=g_hdr)
gov_seen_task = next((t for t in r_all_tasks.json() if t["id"] == task_id), None)
print("Govt sees task status as:", gov_seen_task.get("status") if gov_seen_task else "NOT_FOUND")

print("\n=== 11. DECISION REVIEW & APPROVE DISPATCH ===")
r_recs = client.get(f"/api/v1/ai/incidents/{inc_gps_id}/recommendations", headers=g_hdr)
print("Recommendations status:", r_recs.status_code, "Count:", len(r_recs.json()))
if r_recs.json():
    rec0 = r_recs.json()[0]
    r_app = client.post(f"/api/v1/ai/recommendations/{rec0['id']}/approve", headers=g_hdr, json={"notes": "Approved by Commander"})
    print("Approval status:", r_app.status_code, "New rec status:", r_app.json().get("status"))

print("\n=== 12. NGO INVENTORY & DISPATCH ===")
r_res_list = client.get("/api/v1/resources", headers=n_hdr)
print("NGO resources query status:", r_res_list.status_code, "Items count:", len(r_res_list.json()))

if not r_res_list.json():
    # Seed a resource if none exists
    r_create = client.post("/api/v1/resources", headers=n_hdr, json={
        "owner_type": "NGO",
        "category": "FOOD",
        "resource_name": "Emergency MRE Ration Packs",
        "total_quantity": 100,
        "unit": "packs",
        "location_lat": 13.0827,
        "location_lng": 80.2707
    })
    print("Created test resource:", r_create.status_code)
    r_res_list = client.get("/api/v1/resources", headers=n_hdr)

res0 = r_res_list.json()[0]
init_qty = res0["available_quantity"]
res_id = res0["id"]
print(f"  Resource {res_id} ({res0['resource_name']}): initial available stock = {init_qty}")

# Valid dispatch
r_disp = client.post(f"/api/v1/resources/{res_id}/dispatch?quantity=5", headers=n_hdr)
print("  Dispatch 5 status:", r_disp.status_code, "Remaining available stock:", r_disp.json().get("available_quantity"))
assert r_disp.json().get("available_quantity") == init_qty - 5

# Insufficient dispatch
r_insuf = client.post(f"/api/v1/resources/{res_id}/dispatch?quantity=999999", headers=n_hdr)
print("  Insufficient dispatch status:", r_insuf.status_code, "Detail:", r_insuf.json().get("detail"))
assert r_insuf.status_code == 400

# Verify stock unchanged after failure
r_check = client.get(f"/api/v1/resources", headers=n_hdr)
res_after = next(r for r in r_check.json() if r["id"] == res_id)
print("  Stock after failed dispatch:", res_after["available_quantity"], "(preserved:", res_after["available_quantity"] == init_qty - 5, ")")
assert res_after["available_quantity"] == init_qty - 5

print("\n=== 13. GIS KNN & RADIUS RETEST ===")
r_knn = client.post("/api/v1/gis/spatial-query", json={"query_type": "KNN", "latitude": 13.0827, "longitude": 80.2707, "target_layer": "shelter"})
print("KNN Shelter count:", r_knn.json().get("results_count"))

r_rad10 = client.post("/api/v1/gis/spatial-query", json={"query_type": "RADIUS", "latitude": 13.0827, "longitude": 80.2707, "radius_km": 10.0})
print("RADIUS 10km count:", r_rad10.json().get("results_count"))

r_rad15 = client.post("/api/v1/gis/spatial-query", json={"query_type": "RADIUS", "latitude": 13.0827, "longitude": 80.2707, "radius_km": 15.0})
print("RADIUS 15km count:", r_rad15.json().get("results_count"))

r_bbox = client.post("/api/v1/gis/spatial-query", json={"query_type": "BBOX", "bbox": [80.20, 13.00, 80.35, 13.15]})
print("BBOX count:", r_bbox.json().get("results_count"))

print("\n=== 14. SCENARIO LABORATORY & COMPARE ===")
r_scens = client.get("/api/v1/simulation/scenarios", headers=g_hdr)
print("Simulation scenarios count:", len(r_scens.json()))
scen_ids = [s["id"] for s in r_scens.json()[:2]]

if scen_ids:
    print("Testing scenario_id:", scen_ids[0])
    r_sim = client.post("/api/v1/simulation/run", headers=g_hdr, json={"scenario_id": scen_ids[0]})
    print("Simulation run status:", r_sim.status_code)
    sim_data = r_sim.json()
    print("Simulation run response:", sim_data if r_sim.status_code != 200 else {
        "status": sim_data.get("status"),
        "fingerprint": sim_data.get("fingerprint") or sim_data.get("run_fingerprint"),
        "delta_keys": list(sim_data.get("delta", {}).keys())
    })
    
    r_comp = client.post("/api/v1/simulation/scenarios/compare", headers=g_hdr, json={"scenario_ids": scen_ids})
    print("Comparison status:", r_comp.status_code, "Comparison count:", len(r_comp.json().get("comparisons", [])))

print("\n=== AUDIT RUN COMPLETED SUCCESSFULLY ===")
