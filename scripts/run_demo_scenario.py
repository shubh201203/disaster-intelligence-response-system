import sys
import os
import time

# Set DATABASE_URL fallback if PostgreSQL is not running locally
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///./demo_dirs.db"

# Suppress GeoAlchemy DDL for SQLite demo execution if SQLite is active
if os.environ.get("DATABASE_URL", "").startswith("sqlite"):
    import geoalchemy2.admin
    import geoalchemy2.admin.dialects.sqlite
    from geoalchemy2.types import _GISType
    from geoalchemy2 import Geometry
    from sqlalchemy.ext.compiler import compiles

    geoalchemy2.admin.dialects.sqlite.after_create = lambda table, bind, **kw: None
    geoalchemy2.admin.dialects.sqlite.before_drop = lambda table, bind, **kw: None
    geoalchemy2.admin.after_create = lambda *args, **kwargs: None
    geoalchemy2.admin.before_drop = lambda *args, **kwargs: None
    _GISType.bind_expression = lambda self, bindvalue: bindvalue
    _GISType.column_expression = lambda self, colexpr: colexpr

    @compiles(Geometry, 'sqlite')
    def compile_geometry_sqlite(element, compiler, **kw):
        return "TEXT"

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, Incident, RescueTask, Resource, Shelter, Alert, AuditLog
from app.schemas.incident import IncidentCreate
from app.services.incident_service import IncidentService
from app.services.rescue_service import RescueService
from app.services.resource_service import ResourceService
from app.services.audit_service import AuditService
from app.ai.severity.service import SeverityService
from app.ai.priority.service import PriorityService
from app.ai.duplicate_detection.service import DuplicateDetectionService
from app.core.security import get_password_hash
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)

def print_step(step_num: int, title: str, details: str):
    print(f"\n[STEP {step_num}] {title}")
    print(f" -> {details}")

def run_demo_scenario():
    print_header("DIRS Phase 3A — AI-Assisted Disaster Intelligence Demo Scenario")
    print("Scenario: Category 4 Cyclone 'Vardah' & Secondary Flash Flooding")

    db: Session = SessionLocal()

    try:
        # 1. Reset Database & Create Roles
        print_step(1, "Resetting Scenario Database", "Clearing existing records and setting up role accounts...")
        Base.metadata.create_all(bind=engine)
        db.query(AuditLog).delete()
        db.query(RescueTask).delete()
        db.query(Alert).delete()
        db.query(Resource).delete()
        db.query(Shelter).delete()
        db.query(Incident).delete()
        db.query(User).delete()
        db.commit()

        pwd = get_password_hash("DemoPass123!")
        admin_user = User(email="govt_admin@dirs.gov", hashed_password=pwd, full_name="Disaster Commissioner", role="GOVT", phone="+91-11-20000000")
        citizen_user = User(email="citizen_rahul@dirs.org", hashed_password=pwd, full_name="Rahul Sharma", role="CITIZEN", phone="+91-9876543210")
        vol_user = User(email="volunteer_priya@dirs.org", hashed_password=pwd, full_name="Priya Patel (First Aid/Rescue)", role="VOLUNTEER", phone="+91-9876543211")
        ngo_user = User(email="ngo_relief@dirs.org", hashed_password=pwd, full_name="Red Cross Relief Hub", role="NGO", phone="+91-9876543212")
        db.add_all([admin_user, citizen_user, vol_user, ngo_user])
        db.commit()

        # Seed initial Shelters & NGO Stock
        is_sqlite = os.environ.get("DATABASE_URL", "").startswith("sqlite")
        geom_val = None if is_sqlite else ST_SetSRID(ST_MakePoint(80.2780, 13.0870), 4326)

        shelter = Shelter(
            name="Sector 5 Emergency Relief Center",
            address="10 Sector 5 Boulevard",
            total_capacity=500,
            current_occupancy=120,
            latitude=13.0870,
            longitude=80.2780,
            geom=geom_val,
            has_medical=True,
            has_food=True,
            has_water=True,
            disaster_risk_level="LOW",
            status="OPEN"
        )
        medical_stock = Resource(
            owner_type="NGO",
            owner_id=ngo_user.id,
            category="MEDICINE",
            resource_name="Trauma & First Aid Kits",
            total_quantity=250,
            available_quantity=250,
            unit="kits",
            location_lat=13.0900,
            location_lng=80.2700
        )
        db.add_all([shelter, medical_stock])
        db.commit()

        # Step 2: Emergency Alert
        print_step(2, "Broadcasting Meteorological Emergency Alert", "Admin broadcasts Cyclone & Flood Evacuation Alert")
        alert = Alert(
            title="EMERGENCY: Cyclone Vardah Landfall & Flash Flooding",
            message="Category 4 Cyclone approaching coastal district. Evacuate low-lying riverfront zones immediately.",
            alert_type="EVACUATION",
            target_zone_lat=13.0827,
            target_zone_lng=80.2707,
            radius_km=10.0,
            created_by=admin_user.id
        )
        db.add(alert)
        db.commit()
        print(f" -> Alert Created: '{alert.title}' (ID: {alert.id})")

        # Step 3: Citizen Incident Report & SOS
        print_step(3, "Citizen Distress SOS & Incident Submission", "Citizen Rahul reports urgent rooftop flooding")
        incident_in = IncidentCreate(
            title="Severe Rooftop Flooding - 8 Citizens Trapped",
            disaster_type="FLOOD",
            description="Rising floodwaters have reached 6 feet. 8 family members including children trapped on rooftop.",
            latitude=13.0827,
            longitude=80.2707,
            location_address="42 Riverfront Lane, Block B",
            people_affected=8,
            injuries=2,
            vulnerable_count=3
        )
        incident = IncidentService.create_incident(db, incident_in, reporter=citizen_user)
        print(f" -> Incident Generated: [{incident.incident_code}] '{incident.title}' | Initial Status: {incident.status}")

        # Step 4: AI Severity Classifier & Explainability
        print_step(4, "AI Incident Severity Classifier", "AI ML model predicts severity and generates explainable breakdown")
        sev_res = SeverityService.analyze_incident_severity(db, incident)
        print(f" [AI PREDICTION] -> Predicted Severity: {sev_res.prediction} | Confidence: {sev_res.confidence}% (Review Required: {sev_res.requires_human_review})")
        print(" [AI EXPLANATION FACTORS]:")
        for f in sev_res.factors:
            print(f"    * {f.feature}: {f.description} (+{f.impact} pts)")

        # Step 5: AI Priority Scoring Engine
        print_step(5, "AI Intelligent Priority Engine", "Calculating normalized 0-100 priority score with centralized weights")
        prio_res = PriorityService.calculate_incident_priority(db, incident)
        print(f" [AI PRIORITY] -> Priority Score: {prio_res.priority_score} / 100 ({prio_res.classification})")
        print(" [AI PRIORITY BREAKDOWN]:")
        for factor_name, pts in prio_res.breakdown.items():
            print(f"    * {factor_name}: {pts} pts")

        # Step 6: Spatio-Temporal Duplicate Detection
        print_step(6, "AI Duplicate & Related Incident Detection", "Checking multi-criteria similarity against nearby reports")
        dup_inc = IncidentCreate(
            title="Rooftop Flood Water Trapped Citizens",
            disaster_type="FLOOD",
            description="Water overflowing into house, 8 people trapped on roof",
            latitude=13.0829, # ~25m away
            longitude=80.2708,
            location_address="Riverfront Block B",
            people_affected=8
        )
        incident2 = IncidentService.create_incident(db, dup_inc, reporter=citizen_user)
        dup_res = DuplicateDetectionService.detect_duplicates(db, incident2)
        print(f" [AI DUPLICATE DETECTOR] -> Candidates Found: {dup_res.duplicate_count}")
        for cand in dup_res.candidates:
            print(f"    * Candidate: {cand.candidate_code} | Similarity Score: {cand.similarity_score * 100:.1f}% | Recommendation: {cand.recommendation}")
            print(f"      Evidence: Distance: {cand.evidence.distance_m}m, Time Delta: {cand.evidence.time_difference_min}m, Text Sim: {cand.evidence.text_similarity * 100:.1f}%")

        # Step 7: Government Verification & Decision
        print_step(7, "Government Command Center Human Verification", "Government Officer inspects AI findings and verifies incident")
        verified_incident = IncidentService.transition_incident_status(
            db=db,
            incident=incident,
            target_status="VERIFIED",
            actor=admin_user,
            notes="HUMAN VERIFICATION: Approved AI CRITICAL recommendation"
        )
        print(f" [HUMAN DECISION] -> Status Transitioned: {verified_incident.status}")

        # Step 8: Volunteer Recommendation & Task Dispatch
        print_step(8, "Volunteer Rescue Task Matching & Dispatch", "Engine matches nearest certified volunteer")
        task = RescueService.assign_rescue_task(
            db=db,
            incident_id=verified_incident.id,
            assigned_type="VOLUNTEER",
            assigned_id=vol_user.id,
            admin=admin_user
        )
        print(f" -> Rescue Task Created: [Task #{task.id}] Assigned to {vol_user.full_name} | Initial Task Status: {task.status}")

        # Step 9: Volunteer Rescue Lifecycle Execution
        print_step(9, "Volunteer Task Lifecycle Progression", "Priya executes rescue step-by-step")
        statuses = ["ACCEPTED", "EN_ROUTE", "ARRIVED", "RESCUE_STARTED", "COMPLETED"]
        for st in statuses:
            task = RescueService.transition_task_status(db=db, task=task, target_status=st, actor=vol_user)
            print(f"   [Volunteer Action] -> Status transitioned to: {task.status}")

        # Step 10: Incident Resolution & Audit Log Summary
        print_step(10, "Incident Resolution & Audit Trail Verification", "Incident automatically marked RESOLVED upon rescue task completion")
        db.refresh(verified_incident)
        print(f" -> Incident Status: {verified_incident.status} (Resolved at: {verified_incident.resolved_at})")

        # Step 11: Phase 3B Computer Vision Damage Assessment
        print_step(11, "Phase 3B Computer Vision Damage Assessment", "Analyzing structure damage from incident evidence photo")
        from app.ai.computer_vision.service import ComputerVisionService
        cv_result = ComputerVisionService.analyze_incident_image(db, verified_incident)
        print(f" [AI CV] -> Damage Class: {cv_result.damage_class} | Confidence: {cv_result.confidence}% | Heatmap: {cv_result.explanation_metadata.get('saliency_heatmap_4x4')}")

        # Step 12: Phase 3B Disaster & Meteorological Risk Prediction
        print_step(12, "Phase 3B Disaster Risk Prediction Engine", "Predicting meteorological disaster risk and contributing environmental factors")
        from app.ai.risk_prediction.service import RiskPredictionService
        env_data = {"rainfall_mm": 240.0, "wind_speed_kmh": 130.0, "river_level_m": 6.8, "population_exposure": 7500.0, "disaster_type": "CYCLONE"}
        risk_res = RiskPredictionService.calculate_risk(db, incident=verified_incident, environmental_data=env_data)
        print(f" [AI RISK] -> Risk Level: {risk_res.risk_level} | Score: {risk_res.risk_score}/100 | Confidence: {risk_res.confidence}%")
        print(" [AI RISK FACTORS]:")
        for f in risk_res.contributing_factors:
            print(f"    * {f['feature']}: {f['description']} (+{f['impact']} pts)")

        # Step 13: Phase 3B Resource Demand Prediction & Shortage Detection
        print_step(13, "Phase 3B Resource Demand & Shortage Intelligence", "Predicting resource demand and identifying stock shortages")
        from app.ai.resource_demand.service import ResourceDemandService
        demand_res = ResourceDemandService.predict_incident_demand(db, verified_incident)
        water_qty = demand_res.predictions.get('water_packs', {}).get('quantity', 0)
        food_qty = demand_res.predictions.get('food_packets', {}).get('quantity', 0)
        med_qty = demand_res.predictions.get('medical_kits', {}).get('quantity', 0)
        print(f" [AI DEMAND FORECAST] -> Rations: {food_qty} units | Water: {water_qty} L | Medical: {med_qty} kits")
        print(f" [SHORTAGE ALERTS] -> Shortages Detected: {len(demand_res.shortages_detected)} items")

        # Step 14: Phase 3B Government AI Prediction Override
        print_step(14, "Phase 3B Government Officer AI Prediction Override", "Overriding risk prediction with audit log")
        overridden = RiskPredictionService.override_risk_assessment(
            db=db,
            assessment_id=risk_res.id,
            override_level="EXTREME",
            notes="Government Officer elevated risk level to EXTREME due to high tidal surge",
            reviewer=admin_user
        )
        print(f" [HUMAN OVERRIDE] -> Original AI Level: {risk_res.risk_level} -> Overridden Level: {overridden.override_level} | Notes: '{overridden.override_notes}'")

        # Step 15: Phase 3C Authoritative Knowledge Seeding
        print_step(15, "Phase 3C Authoritative Knowledge Seeding & Vector Indexing", "Seeding NDMA, FEMA, WHO guidelines into vector index")
        from app.ai.rag.service import RAGService
        kb_res = RAGService.seed_authoritative_knowledge_base(db)
        print(f" [RAG KB SEED] -> Status: {kb_res['status']} | Documents: {kb_res['documents']}")

        # Step 16: Phase 3C Grounded RAG Query Execution
        print_step(16, "Phase 3C Grounded RAG Query & Copilot Retrieval", "Executing grounded RAG query for flood evacuation guidance")
        rag_res = RAGService.query_copilot(db=db, query="What NDMA flood evacuation and shelter protocols should be enacted?", incident_id=verified_incident.id)
        print(f" [RAG COPILOT] -> Grounded: {rag_res.is_grounded} | Confidence: {rag_res.confidence}% | Provider: {rag_res.provider}")
        print(f" [EXECUTIVE SUMMARY] -> {rag_res.summary}")
        print(f" [FACTS EXTRACTED] -> {len(rag_res.facts)} system & KB facts retrieved")
        for fact in rag_res.facts[:3]:
            print(f"    * Fact: {fact.statement} (Ref: {fact.evidence_ref})")
        print(f" [CITATIONS] -> {len(rag_res.citations)} authoritative citations attached")
        for cite in rag_res.citations[:2]:
            print(f"    * Citation: [{cite.organization}] {cite.title} - Section: {cite.section} ({cite.similarity_score * 100:.1f}% match)")

        # Step 17: Phase 3C AI Structured Recommendation Generation
        print_step(17, "Phase 3C AI Structured Recommendation Generation", "Generating structured decision recommendations for incident")
        from app.ai.recommendations.engine import RecommendationEngine
        from app.ai.recommendations.service import RecommendationService
        saved_recs = RecommendationEngine.generate_incident_recommendations(db, verified_incident)
        print(f" [AI RECOMMENDATIONS] -> Generated {len(saved_recs)} Actionable Recommendations")
        for r in saved_recs:
            print(f"    * Rec [{r.priority}] {r.action_title} (ID: {r.id[:8]}...) | Rationale: {r.rationale}")

        # Step 18: Phase 3C Government Human-in-the-Loop Decision Approval
        print_step(18, "Phase 3C Government Recommendation Approval & Audit Trail", "Government Officer accepts recommendation with immutable log")
        target_rec = saved_recs[0]
        accepted_rec = RecommendationService.process_government_decision(
            db=db,
            recommendation_id=target_rec.id,
            action="ACCEPTED",
            notes="Government Officer approved shelter evacuation deployment.",
            modified_values=None,
            reviewer=admin_user
        )
        print(f" [HUMAN DECISION] -> Recommendation {accepted_rec.id[:8]}... Status Transitioned to: {accepted_rec.status}")

        logs = db.query(AuditLog).all()
        print(f" -> Total Immutable Audit Log Entries Recorded: {len(logs)}")
        for log in logs[:5]:
            print(f"    * [{log.timestamp}] Action: {log.action} | Target Entity: {log.target_entity}")

        print_header("Phase 3A + 3B + 3C AI Disaster Intelligence Demo Scenario Completed Successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    run_demo_scenario()

