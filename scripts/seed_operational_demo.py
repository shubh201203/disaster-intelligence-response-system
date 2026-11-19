"""
DIRS — Comprehensive Synthetic Demonstration Dataset Population Script
Classification: SYNTHETIC CALIBRATED DEMONSTRATION DATASET
Reference: Chennai / Tamil Nadu Disaster Operations Corridor (12.65°N - 13.18°N, 79.95°E - 80.30°E)
Deterministic Seed: 42

Strict Scope Boundaries:
- Data population only. Zero changes to optimization, simulation, or GIS algorithms.
- Full demographic conservation: sum(evacuation_demographics.values()) == people_affected.
- Zero fake historical performance ratings or SLA percentages.
- Idempotent and deterministic execution.
"""

import os
import sys
import math
import random
import argparse
from datetime import datetime, timezone

# Add backend directory to sys.path (supports both host and docker container)
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(script_dir, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(script_dir, "..", "backend")))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.database import Base, SessionLocal, engine as default_engine
from app.models.user import User, UserRole, CitizenProfile, VolunteerProfile, NGOProfile
from app.models.incident import Incident, IncidentReport, IncidentCluster
from app.models.shelter import Shelter
from app.models.resource import Resource, ResourceRequest
from app.models.vehicle import Vehicle
from app.models.rescue import RescueTask, RoadBlockage
from app.models.alert import Alert
from app.models.ai import AIPrediction, CVDamageAssessment, RiskAssessment, ResourceDemandPrediction
from app.models.rag import KnowledgeDocument, KnowledgeChunk, RAGQueryLog, Recommendation, RecommendationDecision
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog
from app.models.simulation import SimulationScenario
from app.core.security import get_password_hash
from app.ai.rag.service import RAGService
from app.ai.rag.ingestion.chunker import chunk_text_content
from app.ai.rag.embeddings.model import EmbeddingProvider
import hashlib

try:
    from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
except ImportError:
    ST_SetSRID, ST_MakePoint = None, None


def get_db_session(db_url: str = None):
    """Returns a database engine and session for PostgreSQL or SQLite."""
    if db_url:
        if db_url.startswith("sqlite"):
            # Suppress GeoAlchemy DDL for SQLite
            import geoalchemy2.admin
            import geoalchemy2.admin.dialects.sqlite
            from geoalchemy2.types import _GISType
            from geoalchemy2 import Geometry
            from sqlalchemy.ext.compiler import compiles

            geoalchemy2.admin.dialects.sqlite.after_create = lambda *a, **k: None
            geoalchemy2.admin.dialects.sqlite.before_drop = lambda *a, **k: None
            geoalchemy2.admin.after_create = lambda *a, **k: None
            geoalchemy2.admin.before_drop = lambda *a, **k: None
            _GISType.bind_expression = lambda self, b: b
            _GISType.column_expression = lambda self, c: c

            @compiles(Geometry, 'sqlite')
            def compile_geom(el, comp, **kw): return "TEXT"

            eng = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            eng = create_engine(db_url)
        Base.metadata.create_all(bind=eng)
        from sqlalchemy.orm import sessionmaker
        SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=eng)
        return eng, SessionMaker()
    else:
        Base.metadata.create_all(bind=default_engine)
        return default_engine, SessionLocal()


def seed_operational_demo(db: Session, engine_instance):
    rng = random.Random(42)
    is_sqlite = engine_instance.dialect.name == "sqlite"

    print("================================================================================")
    print("DIRS — COMPREHENSIVE SYNTHETIC DEMONSTRATION DATASET POPULATION")
    print(f"Target Database Dialect: {engine_instance.dialect.name}")
    print("Seed: 42 (Deterministic & Idempotent)")
    print("================================================================================")

    # -------------------------------------------------------------------------
    # 1. Clean Slate for Seed Demonstration Tables (Preserving Schema & Audits)
    # -------------------------------------------------------------------------
    print("\n[Step 1/8] Clearing existing demo entities...")
    db.query(Alert).delete()
    db.query(RescueTask).delete()
    db.query(RoadBlockage).delete()
    db.query(Vehicle).delete()
    db.query(ResourceRequest).delete()
    db.query(Resource).delete()
    db.query(Shelter).delete()
    # Delete child tables referencing incidents
    db.query(RecommendationDecision).delete()
    db.query(Recommendation).delete()
    db.query(OptimizationOverrideLog).delete()
    db.query(OptimizationRecommendation).delete()
    db.query(OptimizationRun).delete()
    db.query(RAGQueryLog).delete()
    db.query(AIPrediction).delete()
    db.query(CVDamageAssessment).delete()
    db.query(RiskAssessment).delete()
    db.query(ResourceDemandPrediction).delete()
    db.query(IncidentReport).delete()
    db.query(IncidentCluster).delete()
    db.query(Incident).delete()
    db.query(CitizenProfile).delete()
    db.query(VolunteerProfile).delete()
    db.query(NGOProfile).delete()
    # Delete demo simulation scenarios
    db.query(SimulationScenario).filter(SimulationScenario.id.like("SCEN_DEMO_%")).delete(synchronize_session=False)
    db.commit()

    # -------------------------------------------------------------------------
    # 2. Users & Demographic Profiles
    # -------------------------------------------------------------------------
    print("\n[Step 2/8] Seeding operational role users & specialized profiles...")

    # Helper function to get or create a user
    def upsert_user(email, password, full_name, role, phone):
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                role=role,
                phone=phone,
                is_active=True
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        else:
            u.full_name = full_name
            u.role = role
            u.phone = phone
            u.is_active = True
            db.commit()
        return u

    # 2.1 Core Quick-Login Demo Users
    govt_admin = upsert_user("admin@dirs.gov", "Admin123!", "Disaster Commissioner [DEMO]", "GOVT", "+91-44-25619001")
    demo_citizen = upsert_user("citizen@dirs.org", "Citizen123!", "Rahul Sharma [DEMO]", "CITIZEN", "+91-9876543210")
    demo_volunteer = upsert_user("volunteer@dirs.org", "Volunteer123!", "Priya Patel [DEMO]", "VOLUNTEER", "+91-9876543211")
    demo_ngo = upsert_user("ngo@dirs.org", "Ngo123!", "Global Relief Foundation [DEMO]", "NGO", "+91-44-28271100")

    # 2.2 Secondary NGO
    ngo_consortium = upsert_user("redcross_tamilnadu@dirs.org", "Ngo123!", "Tamil Nadu Emergency Relief Consortium [DEMO]", "NGO", "+91-44-28554400")

    # NGO Profiles
    db.add(NGOProfile(
        user_id=demo_ngo.id,
        org_name="Global Relief Foundation",
        registration_no="NGO-TN-2024-8891",
        contact_person="Arunachalam Venkatesh",
        address="14 Montieth Road, Egmore Logistics Compound, Chennai",
        verified=True
    ))
    db.add(NGOProfile(
        user_id=ngo_consortium.id,
        org_name="Tamil Nadu Emergency Relief Consortium",
        registration_no="NGO-TN-2023-4510",
        contact_person="Dr. Meenakshi Sundaram",
        address="45 Rajaji Salai, Port Gate 3, Royapuram, Chennai",
        verified=True
    ))

    # Citizen Profiles (Demo + 5 Synthetic Citizens)
    citizens_data = [
        (demo_citizen, "Sunita Sharma", "+91-9876500001", "12 Riverfront Colony, Adyar, Chennai", 13.0060, 80.2570),
        (upsert_user("citizen.anand@dirs.org", "Citizen123!", "Anand Krishnan [DEMO]", "CITIZEN", "+91-9876500002"),
         "Kavitha Anand", "+91-9876500022", "88 100-Feet Road, Velachery, Chennai", 12.9780, 80.2180),
        (upsert_user("citizen.fatima@dirs.org", "Citizen123!", "Fatima Zahra [DEMO]", "CITIZEN", "+91-9876500003"),
         "Rashid Zahra", "+91-9876500033", "23 North Beach Road, Royapuram, Chennai", 13.1100, 80.2950),
        (upsert_user("citizen.selvam@dirs.org", "Citizen123!", "Selvam Murugan [DEMO]", "CITIZEN", "+91-9876500004"),
         "Mala Selvam", "+91-9876500044", "102 GST Road, Tambaram East, Chennai", 12.9250, 80.1200),
        (upsert_user("citizen.deepa@dirs.org", "Citizen123!", "Deepa Raghavan [DEMO]", "CITIZEN", "+91-9876500005"),
         "Raghavan S.", "+91-9876500055", "34 4th Main Road, Anna Nagar West, Chennai", 13.0850, 80.2100),
        (upsert_user("citizen.karthik@dirs.org", "Citizen123!", "Karthik Subramanian [DEMO]", "CITIZEN", "+91-9876500006"),
         "Uma Subramanian", "+91-9876500066", "17 Lake View Road, Madipakkam, Chennai", 12.9650, 80.1980),
    ]
    for cit_u, contact_name, contact_phone, addr, lat, lng in citizens_data:
        db.add(CitizenProfile(
            user_id=cit_u.id,
            emergency_contact_name=contact_name,
            emergency_contact_phone=contact_phone,
            address=addr,
            latitude=lat,
            longitude=lng
        ))

    # Volunteer Profiles (Demo + 32 Specialized Synthetic Volunteers)
    # Skills distribution: 9 MEDICAL, 10 RESCUE, 7 LOGISTICS, 7 GENERAL = 33 total
    volunteer_roster = [
        # (email, name, category, skills, med_cert, exp_years, vehicle, lat, lng, is_avail)
        ("volunteer@dirs.org", "Priya Patel [DEMO]", "RESCUE", ["First Aid", "Water Rescue", "CPR"], True, 4, "4x4 Rescue Truck", 13.0850, 80.2750, True),
        # MEDICAL (Certified First Responders & Nurses)
        ("vol.med1@dirs.org", "Dr. Rajesh Raman [DEMO]", "MEDICAL", ["Emergency Medicine", "Triage", "Advanced First Aid"], True, 8, "Medical Van", 13.0827, 80.2707, True),
        ("vol.med2@dirs.org", "Nurse Mary Shanthi [DEMO]", "MEDICAL", ["Wound Dressing", "Pediatric First Aid", "CPR"], True, 6, "Two-Wheeler", 13.0067, 80.2020, True),
        ("vol.med3@dirs.org", "Dr. Arvind Swaminathan [DEMO]", "MEDICAL", ["Trauma Care", "Surgical First Aid"], True, 10, "4x4 SUV", 12.9780, 80.2180, True),
        ("vol.med4@dirs.org", "Saritha Balan [DEMO]", "MEDICAL", ["Basic Life Support", "IV Fluids Administration"], True, 3, "Two-Wheeler", 13.0500, 80.2800, True),
        ("vol.med5@dirs.org", "Dr. Harish Kumar [DEMO]", "MEDICAL", ["Disaster Triage", "Infection Control"], True, 7, "Utility Vehicle", 12.9249, 80.1000, True),
        ("vol.med6@dirs.org", "Kavitha Natarajan [DEMO]", "MEDICAL", ["First Aid", "Psychological First Aid"], True, 4, "None", 13.1100, 80.2950, True),
        ("vol.med7@dirs.org", "Dr. Vijay Raghavan [DEMO]", "MEDICAL", ["Paramedic Field Surgery", "Splinting"], True, 9, "Ambulance Van", 13.0400, 80.2400, True),
        ("vol.med8@dirs.org", "Divya Chandran [DEMO]", "MEDICAL", ["Triage Assessment", "Burn Management"], True, 5, "Two-Wheeler", 13.0600, 80.1900, False), # Shift break

        # RESCUE (Boat operators, structural search, flood rescue)
        ("vol.res1@dirs.org", "Karthik Raja [DEMO]", "RESCUE", ["Inflatable Boat Rescue", "Deep Water Navigation"], False, 5, "Rescue Boat Trailer", 13.0050, 80.2500, True),
        ("vol.res2@dirs.org", "Vigneshwaran P. [DEMO]", "RESCUE", ["High-Angle Rope Rescue", "Debris Clearance"], False, 4, "4x4 Truck", 13.0900, 80.2800, True),
        ("vol.res3@dirs.org", "Suresh Gopinath [DEMO]", "RESCUE", ["Swift Water Rescue", "Swimmer Certified"], False, 6, "Two-Wheeler", 12.9800, 80.2300, True),
        ("vol.res4@dirs.org", "Muthu Vel [DEMO]", "RESCUE", ["Chainsaw Operation", "Fallen Tree Removal"], False, 3, "Utility Truck", 12.9500, 80.1400, True),
        ("vol.res5@dirs.org", "Deepak Sundaram [DEMO]", "RESCUE", ["Flood Evacuation", "Life Raft Dispatch"], False, 4, "4x4 SUV", 13.0200, 80.1800, True),
        ("vol.res6@dirs.org", "Gnanavel R. [DEMO]", "RESCUE", ["Collapsed Structure Search", "Night Rescue"], False, 7, "Utility Truck", 13.1200, 80.2100, True),
        ("vol.res7@dirs.org", "Bala Murugan [DEMO]", "RESCUE", ["Water Rescue", "First Aid"], False, 2, "None", 13.0700, 80.2600, True),
        ("vol.res8@dirs.org", "Ashok Varadhan [DEMO]", "RESCUE", ["Heavy Winch Operations", "Vehicle Recovery"], False, 8, "Recovery Vehicle", 12.9300, 80.1300, True),
        ("vol.res9@dirs.org", "Sanjay Ebenezer [DEMO]", "RESCUE", ["Kayaking Evacuation", "Radio Communications"], False, 3, "Two-Wheeler", 12.9900, 80.2600, False),

        # LOGISTICS (Warehousing, supply convoy, forklift, inventory distribution)
        ("vol.log1@dirs.org", "Ramesh Babu [DEMO]", "LOGISTICS", ["Warehouse Management", "Inventory Dispatch"], False, 6, "Cargo Van", 13.0827, 80.2707, True),
        ("vol.log2@dirs.org", "Prasad Narayanan [DEMO]", "LOGISTICS", ["Heavy Truck Driving", "Route Planning"], False, 9, "7-Ton Lorry", 13.0067, 80.2020, True),
        ("vol.log3@dirs.org", "Manikandan S. [DEMO]", "LOGISTICS", ["Water Tanker Coordination", "Sanitation Rations"], False, 4, "Water Bowsing Van", 12.9249, 80.1000, True),
        ("vol.log4@dirs.org", "Gita Krishnan [DEMO]", "LOGISTICS", ["Cold Chain Storage", "Pharma Rationing"], False, 5, "Two-Wheeler", 13.0500, 80.2200, True),
        ("vol.log5@dirs.org", "Thirunavukkarasu K. [DEMO]", "LOGISTICS", ["Heavy Forklift", "Pallet Stacking"], False, 3, "None", 13.1140, 80.1540, True),
        ("vol.log6@dirs.org", "Jagan Mohan [DEMO]", "LOGISTICS", ["Fuel Bowsing", "Emergency Generator Logistics"], False, 7, "Utility Truck", 13.0300, 80.1700, True),
        ("vol.log7@dirs.org", "Anandhi Ravi [DEMO]", "LOGISTICS", ["Supply Sorting", "Emergency Manifests"], False, 2, "None", 12.9600, 80.2100, False),

        # GENERAL (Shelter operations, crowd management, food distribution, registration)
        ("vol.gen1@dirs.org", "Nalini Sundar [DEMO]", "GENERAL", ["Evacuee Registration", "Shelter Management"], False, 4, "Two-Wheeler", 13.0870, 80.2780, True),
        ("vol.gen2@dirs.org", "Senthamil Selvi [DEMO]", "GENERAL", ["Food Ration Distribution", "Hygiene Kits"], False, 3, "None", 13.0950, 80.2650, True),
        ("vol.gen3@dirs.org", "Praveen Joshua [DEMO]", "GENERAL", ["Crowd Control", "Elderly Assistance"], False, 2, "Two-Wheeler", 12.9780, 80.2180, True),
        ("vol.gen4@dirs.org", "Meera Viswanathan [DEMO]", "GENERAL", ["Child Care", "Lost & Found Coordination"], False, 5, "None", 13.0067, 80.2020, True),
        ("vol.gen5@dirs.org", "Arivazhagan M. [DEMO]", "GENERAL", ["Community Announcement", "Loudspeaker Coordination"], False, 3, "Motorcycle", 13.1100, 80.2950, True),
        ("vol.gen6@dirs.org", "Subramanian V. [DEMO]", "GENERAL", ["Drinking Water Stations", "Waste Disposal"], False, 4, "Two-Wheeler", 12.9249, 80.1000, True),
        ("vol.gen7@dirs.org", "Kavya Sridhar [DEMO]", "GENERAL", ["Multi-Language Translation", "Volunteer Helpdesk"], False, 2, "None", 13.0400, 80.2600, False)
    ]

    volunteer_objs = []
    for email, name, skill_cat, skills, med_cert, exp_yrs, v_type, lat, lng, is_avail in volunteer_roster:
        u = upsert_user(email, "Volunteer123!", name, "VOLUNTEER", f"+91-98765{rng.randint(10000, 99999)}")
        vp = VolunteerProfile(
            user_id=u.id,
            skills=skills,
            skill_category=skill_cat,
            assignment_status="UNASSIGNED",
            experience_years=exp_yrs,
            vehicle_type=v_type,
            medical_certified=med_cert,
            verification_status="VERIFIED",
            is_available=is_avail,
            current_lat=lat,
            current_lng=lng,
            max_shift_hours=8.0,
            max_travel_time_mins=45.0,
            shift_availability=["SHIFT_1", "SHIFT_2"] if is_avail else ["SHIFT_2"]
        )
        db.add(vp)
        volunteer_objs.append((u, vp))

    db.commit()
    print(f"  -> Seeded {len(citizens_data)} citizen accounts and {len(volunteer_roster)} volunteer profiles.")

    # -------------------------------------------------------------------------
    # 3. Emergency Shelters
    # -------------------------------------------------------------------------
    print("\n[Step 3/8] Seeding 12 emergency shelters across Chennai disaster corridor...")

    shelters_catalog = [
        # (id, name, address, cap, occ, lat, lng, medical, food, water, power, sanitation, access, risk, status)
        ("SHELTER_DEMO_001", "District Central Emergency Shelter S-104", "Egmore Community Hall, Sector 4, Egmore", 600, 420, 13.0870, 80.2780, True, True, True, True, True, True, "LOW", "OPEN"),
        ("SHELTER_DEMO_002", "North High School Safe Haven S-108", "12 High School Road, Perambur, Chennai", 350, 90, 13.0950, 80.2650, True, True, True, True, True, False, "LOW", "OPEN"),
        ("SHELTER_DEMO_003", "Velachery Multi-Purpose Disaster Shelter S-112", "Velachery Main Bypass, Near Lake Sector", 800, 740, 12.9780, 80.2180, True, True, True, True, True, True, "HIGH", "OPEN"), # High utilization: 92.5%!
        ("SHELTER_DEMO_004", "Guindy Industrial Community Safe Hall S-115", "Guindy Estate Road, Sector 7, Chennai", 450, 180, 13.0067, 80.2020, True, True, True, True, True, True, "LOW", "OPEN"),
        ("SHELTER_DEMO_005", "Mylapore Heritage Relief Center S-120", "28 Kutchery Road, Mylapore, Chennai", 250, 60, 13.0330, 80.2670, False, True, True, True, True, False, "LOW", "OPEN"),
        ("SHELTER_DEMO_006", "Anna Nagar West Community Pavilion S-125", "18 6th Avenue, Anna Nagar West, Chennai", 500, 210, 13.0850, 80.2100, True, True, True, True, True, True, "LOW", "OPEN"),
        ("SHELTER_DEMO_007", "Tambaram Municipal Relief Camp S-130", "Municipal Grounds, Tambaram Sanatorium", 700, 310, 12.9249, 80.1200, True, True, True, True, True, True, "LOW", "OPEN"),
        ("SHELTER_DEMO_008", "Marina Coastal Cyclone Evacuation Center S-135", "Marina Promenade Facility, Triplicane, Chennai", 500, 380, 13.0500, 80.2800, True, True, True, True, True, True, "MEDIUM", "OPEN"),
        ("SHELTER_DEMO_009", "Royapuram Port Workers Safe Haven S-140", "Port Access Road, Royapuram, Chennai", 300, 120, 13.1100, 80.2950, True, True, True, True, True, False, "MEDIUM", "OPEN"),
        ("SHELTER_DEMO_010", "Adyar Riverbank Higher Secondary Shelter S-145", "Gandhi Nagar 3rd Cross, Adyar, Chennai", 350, 290, 13.0060, 80.2570, True, True, True, True, True, True, "HIGH", "OPEN"),
        ("SHELTER_DEMO_011", "Saidapet Government Model School Shelter S-150", "Jones Road, Saidapet Canal Side, Chennai", 450, 150, 13.0180, 80.2220, True, True, True, True, True, False, "LOW", "OPEN"),
        ("SHELTER_DEMO_012", "Chromepet Sports Complex Emergency Haven S-155", "Radha Nagar Main Road, Chromepet, Chennai", 500, 45, 12.9520, 80.1410, False, True, True, True, True, True, "LOW", "OPEN")
    ]

    shelter_objs = []
    for s_id, name, addr, cap, occ, lat, lng, has_med, has_fd, has_wt, pwr, sanit, access, risk, stat in shelters_catalog:
        geom_val = None if is_sqlite or ST_SetSRID is None else ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        s = Shelter(
            id=s_id,
            name=name,
            address=addr,
            total_capacity=cap,
            current_occupancy=occ,
            latitude=lat,
            longitude=lng,
            geom=geom_val,
            has_medical=has_med,
            has_food=has_fd,
            has_water=has_wt,
            power_available=pwr,
            sanitation_available=sanit,
            accessibility_features=access,
            disaster_compatibility=["FLOOD", "CYCLONE"],
            disaster_risk_level=risk,
            status=stat,
            last_verified_at=datetime.now(timezone.utc)
        )
        db.add(s)
        shelter_objs.append(s)

    db.commit()
    tot_cap = sum(s.total_capacity for s in shelter_objs)
    tot_occ = sum(s.current_occupancy for s in shelter_objs)
    print(f"  -> Seeded 12 shelters. Total Capacity: {tot_cap:,}, Current Occupancy: {tot_occ:,} ({tot_occ/tot_cap*100:.1f}%).")

    # -------------------------------------------------------------------------
    # 4. Supply Depots & Multi-Commodity Resources
    # -------------------------------------------------------------------------
    print("\n[Step 4/8] Seeding 5 regional supply depots stocking 6 canonical commodities...")

    depots_meta = [
        ("DEPOT_CENTRAL", "MGR Central Emergency Logistics Hub", 13.0827, 80.2707, "GOVT", govt_admin.id),
        ("DEPOT_GUINDY", "Guindy South Distribution Depot", 13.0067, 80.2020, "GOVT", govt_admin.id),
        ("DEPOT_TAMBARAM", "Tambaram Regional Supply Stockpile", 12.9249, 80.1000, "NGO", demo_ngo.id),
        ("DEPOT_ROYAPURAM", "Royapuram Coastal Logistics Base", 13.1100, 80.2950, "NGO", ngo_consortium.id),
        ("DEPOT_AMBATTUR", "Ambattur Industrial Relief Base", 13.1140, 80.1540, "GOVT", govt_admin.id)
    ]

    # Standard 6 Commodities per Depot
    commodities_spec = [
        ("WATER", "Potable Drinking Water (20L Jerrycans)", "liters", 15000, 12500),
        ("FOOD", "Ready-to-Eat Emergency Food Packs", "packets", 8000, 6800),
        ("MEDICAL_KITS", "Trauma & Emergency Medical Kits", "kits", 400, 320),
        ("RESCUE_EQUIPMENT", "Rescue Equipment (Life Vests, Ropes, Cutters)", "units", 250, 190),
        ("SANITATION_KITS", "Hygiene & Sanitation Disaster Packs", "kits", 1200, 950),
        ("TEMPORARY_SHELTER_SUPPLIES", "Tarpaulins, Bedding & Pop-Up Tents", "units", 500, 410)
    ]

    depot_primary_resources = {}
    resource_count = 0
    total_commodity_units = 0

    for dep_id, dep_name, lat, lng, owner_type, owner_id in depots_meta:
        for idx, (cat, res_label, unit_name, base_tot, base_avail) in enumerate(commodities_spec):
            # Apply slight geographic variation
            scale = 1.2 if "CENTRAL" in dep_id else (0.8 if "ROYAPURAM" in dep_id else 1.0)
            tot_qty = int(base_tot * scale)
            avail_qty = int(base_avail * scale)
            # Short commodity acronym to guarantee len(res_id) <= 32 chars
            cat_short = {
                "WATER": "WTR",
                "FOOD": "FOD",
                "MEDICAL_KITS": "MED",
                "RESCUE_EQUIPMENT": "RSC",
                "SANITATION_KITS": "SAN",
                "TEMPORARY_SHELTER_SUPPLIES": "SHL"
            }.get(cat, cat[:4])
            res_id = f"RES_{dep_id}_{cat_short}"

            res = Resource(
                id=res_id,
                owner_type=owner_type,
                owner_id=owner_id,
                category=cat,
                resource_name=f"{dep_name} — {res_label}",
                total_quantity=tot_qty,
                available_quantity=avail_qty,
                unit=unit_name,
                location_lat=lat,
                location_lng=lng
            )
            db.add(res)
            resource_count += 1
            total_commodity_units += avail_qty

            if idx == 0:
                depot_primary_resources[dep_id] = res_id

    db.commit()
    print(f"  -> Seeded {resource_count} resource inventories across 5 depots ({total_commodity_units:,} units available).")

    # -------------------------------------------------------------------------
    # 5. Vehicle Fleet
    # -------------------------------------------------------------------------
    print("\n[Step 5/8] Seeding 12 disaster response and logistics vehicles...")

    vehicles_catalog = [
        # (code, type, depot_id, wt_kg, vol_m3, lat, lng, status, owner_type, owner_id)
        ("DEMO-VEH-01", "TRUCK", "DEPOT_CENTRAL", 7500.0, 30.0, 13.0827, 80.2707, "AVAILABLE", "GOVT", govt_admin.id),
        ("DEMO-VEH-02", "TRUCK", "DEPOT_CENTRAL", 7500.0, 30.0, 13.0827, 80.2707, "AVAILABLE", "GOVT", govt_admin.id),
        ("DEMO-VEH-03", "AMBULANCE", "DEPOT_CENTRAL", 1500.0, 10.0, 13.0827, 80.2707, "AVAILABLE", "GOVT", govt_admin.id),
        ("DEMO-VEH-04", "VAN", "DEPOT_CENTRAL", 2500.0, 15.0, 13.0827, 80.2707, "AVAILABLE", "GOVT", govt_admin.id),
        ("DEMO-VEH-05", "TRUCK", "DEPOT_GUINDY", 7500.0, 30.0, 13.0067, 80.2020, "AVAILABLE", "GOVT", govt_admin.id),
        ("DEMO-VEH-06", "BOAT", "DEPOT_GUINDY", 1200.0, 8.0, 13.0067, 80.2020, "AVAILABLE", "GOVT", govt_admin.id),
        ("DEMO-VEH-07", "AMBULANCE", "DEPOT_GUINDY", 1500.0, 10.0, 13.0067, 80.2020, "ASSIGNED", "GOVT", govt_admin.id),
        ("DEMO-VEH-08", "TRUCK", "DEPOT_TAMBARAM", 5000.0, 25.0, 12.9249, 80.1000, "AVAILABLE", "NGO", demo_ngo.id),
        ("DEMO-VEH-09", "VAN", "DEPOT_TAMBARAM", 2000.0, 12.0, 12.9249, 80.1000, "IN_TRANSIT", "NGO", demo_ngo.id),
        ("DEMO-VEH-10", "BOAT", "DEPOT_ROYAPURAM", 1200.0, 8.0, 13.1100, 80.2950, "AVAILABLE", "NGO", ngo_consortium.id),
        ("DEMO-VEH-11", "AMBULANCE", "DEPOT_ROYAPURAM", 1500.0, 10.0, 13.1100, 80.2950, "ASSIGNED", "NGO", ngo_consortium.id),
        ("DEMO-VEH-12", "VAN", "DEPOT_AMBATTUR", 2500.0, 15.0, 13.1140, 80.1540, "MAINTENANCE", "GOVT", govt_admin.id)
    ]

    for v_code, v_type, dep_key, wt, vol, lat, lng, v_stat, o_type, o_id in vehicles_catalog:
        v = Vehicle(
            id=f"VEH_{v_code}",
            vehicle_code=v_code,
            vehicle_type=v_type,
            owner_type=o_type,
            owner_id=o_id,
            capacity_weight_kg=wt,
            capacity_volume_m3=vol,
            current_location_lat=lat,
            current_location_lng=lng,
            depot_id=depot_primary_resources.get(dep_key),
            status=v_stat,
            is_active=(v_stat != "MAINTENANCE"),
            operational_constraints={"flood_capable": (v_type == "BOAT"), "max_speed_kmh": 60}
        )
        db.add(v)

    db.commit()
    print(f"  -> Seeded 12 response vehicles (7 Available, 3 Assigned, 1 In Transit, 1 Maintenance).")

    # -------------------------------------------------------------------------
    # 6. Incidents & Demographic Conservation
    # -------------------------------------------------------------------------
    print("\n[Step 6/8] Seeding 20 realistic incidents with strict demographic conservation...")

    incidents_spec = [
        # (code, title, type, prio_lvl, prio_score, sev_lvl, status, lat, lng, addr, people, vuln, inj, skills, desc)
        ("INC-DEMO-1001", "Severe Adyar River Flooding & Inundation Zone A", "FLOOD", "CRITICAL", 96.0, "CRITICAL", "VERIFIED",
         13.0060, 80.2570, "Adyar Bridge & Riverfront Colony, Chennai", 280, 56, 28, {"MEDICAL": 4, "RESCUE": 6, "GENERAL": 4},
         "High velocity overflow from Chembarambakkam reservoir release. Riverbank informal settlements submerged under 1.8m water."),

        ("INC-DEMO-1002", "Velachery Lake Breach & Residential Waterlogging", "FLOOD", "CRITICAL", 94.0, "CRITICAL", "VERIFIED",
         12.9780, 80.2180, "Bypass Road & AGS Colony, Velachery", 320, 64, 32, {"MEDICAL": 5, "RESCUE": 8, "GENERAL": 5},
         "Retention lake breach with rapid water progression into ground floors. Over 100 residents marooned on second-floor balconies."),

        ("INC-DEMO-1003", "Ennore Coastal Cyclone Storm Surge & Port Road Cutoff", "CYCLONE", "CRITICAL", 92.0, "CRITICAL", "VERIFIED",
         13.2000, 80.3200, "Ennore Port Access Corridor, Chennai", 210, 42, 21, {"MEDICAL": 3, "RESCUE": 5, "LOGISTICS": 4},
         "Category 4 severe cyclonic gusts (115 km/h) with 2.1m storm surge inundating coastal fishing settlements and port expressway."),

        ("INC-DEMO-1004", "Saidapet Canal Overflow & Structural Embankment Threat", "FLOOD", "CRITICAL", 90.0, "CRITICAL", "IN_PROGRESS",
         13.0180, 80.2220, "Jones Road & Canal Embankment, Saidapet", 190, 38, 19, {"MEDICAL": 3, "RESCUE": 4, "GENERAL": 3},
         "Canal wall fracture near low-lying railway underpass. Critical threat of embankment wash-out requiring immediate structural shoring."),

        ("INC-DEMO-1005", "Madipakkam Sector 4 Flash Flooding", "FLOOD", "HIGH", 86.0, "HIGH", "VERIFIED",
         12.9650, 80.1980, "Karthikeyapuram, Madipakkam, Chennai", 140, 28, 14, {"MEDICAL": 2, "RESCUE": 3, "GENERAL": 2},
         "Severe storm drain backup. Residential access roads submerged under 1.2m of stagnant muddy water with power lines downed."),

        ("INC-DEMO-1006", "Royapuram Coastal Fishermen Colony Wind Damage", "CYCLONE", "HIGH", 84.0, "HIGH", "VERIFIED",
         13.1100, 80.2950, "North Beach Road, Royapuram, Chennai", 160, 32, 16, {"MEDICAL": 2, "RESCUE": 4, "LOGISTICS": 2},
         "Extensive sheet-metal roofing loss and overturned fishing vessels blocking arterial access to Royapuram harbor."),

        ("INC-DEMO-1007", "Ambattur Industrial Estate Warehouse Electrical Fire", "FIRE", "HIGH", 82.0, "HIGH", "VERIFIED",
         13.1140, 80.1540, "3rd Phase Industrial Estate, Ambattur", 75, 10, 15, {"MEDICAL": 3, "RESCUE": 4, "LOGISTICS": 2},
         "Transformer explosion triggering secondary chemical warehouse fire. Dense toxic smoke plume drifting toward adjacent worker quarters."),

        ("INC-DEMO-1008", "Tambaram Mudichur Submerged Residential Arterial", "FLOOD", "HIGH", 80.0, "HIGH", "ASSIGNED",
         12.9250, 80.0850, "Mudichur Road Junction, Tambaram West", 180, 36, 18, {"MEDICAL": 2, "RESCUE": 4, "GENERAL": 3},
         "Inundation of key arterial connecting GST road to outer ring. Transit restricted exclusively to multi-axle heavy trucks and rescue boats."),

        ("INC-DEMO-1009", "Marina Promenade Coastal Surge & Stall Collapse", "CYCLONE", "HIGH", 78.0, "HIGH", "REPORTED",
         13.0500, 80.2800, "Marina Beach Service Road, Triplicane", 95, 15, 8, {"MEDICAL": 1, "RESCUE": 2, "GENERAL": 2},
         "High tidal waves breaching sea wall onto service road, damaging temporary structures and municipal lifeguard stations."),

        ("INC-DEMO-1010", "Old Washermanpet Structural Wall Failure", "COLLAPSE", "HIGH", 76.0, "HIGH", "REPORTED",
         13.1180, 80.2780, "M.C. Road, Old Washermanpet, Chennai", 60, 12, 10, {"MEDICAL": 2, "RESCUE": 3, "GENERAL": 1},
         "Monsoon rain saturation causing partial exterior masonry failure of 3-story heritage tenement. 4 families trapped on upper floors."),

        ("INC-DEMO-1011", "Kotturpuram Slum Tenement Flood Threat", "FLOOD", "MEDIUM", 68.0, "MEDIUM", "VERIFIED",
         13.0220, 80.2400, "River View Road, Kotturpuram, Chennai", 110, 22, 9, {"MEDICAL": 1, "RESCUE": 2, "GENERAL": 2},
         "Adyar backwaters slowly rising into ground-floor tenements. Evacuation advised before nocturnal high-tide surge."),

        ("INC-DEMO-1012", "St. Thomas Mount Ridge Rockfall & Debris Slip", "LANDSLIDE", "MEDIUM", 65.0, "MEDIUM", "REPORTED",
         13.0030, 80.1900, "Mount Hill Road, St. Thomas Mount", 45, 6, 4, {"RESCUE": 2, "LOGISTICS": 2},
         "Loose boulders and gravel blocking western vehicular access to hilltop relief communications tower."),

        ("INC-DEMO-1013", "George Town Electrical Conduit Smoke & Short Circuit", "FIRE", "MEDIUM", 62.0, "MEDIUM", "REPORTED",
         13.0900, 80.2850, "Armenian Street, George Town, Chennai", 40, 5, 3, {"MEDICAL": 1, "RESCUE": 1, "GENERAL": 1},
         "Underground utility cable short circuit causing street-level smoke and local electrical outage in commercial market corridor."),

        ("INC-DEMO-1014", "Perambur Loco Works Overhead Shed Roof Collapse", "COLLAPSE", "MEDIUM", 60.0, "MEDIUM", "VERIFIED",
         13.1080, 80.2350, "Railway Colony Road, Perambur, Chennai", 50, 8, 6, {"MEDICAL": 2, "RESCUE": 2},
         "Heavy wind gust ripped industrial corrugated iron roof over transit maintenance bay. Minor lacerations reported."),

        ("INC-DEMO-1015", "Tirisulam Quarry Road Mud and Rock Debris Accumulation", "LANDSLIDE", "MEDIUM", 55.0, "MEDIUM", "REPORTED",
         12.9750, 80.1550, "Quarry Bypass Road, Tirisulam, Chennai", 35, 4, 2, {"LOGISTICS": 2, "GENERAL": 1},
         "Hillside surface runoff washing red gravel and clay across secondary bypass, creating skid hazard for emergency logistics."),

        ("INC-DEMO-1016", "Guindy Race Course Sub-drain Overflow", "FLOOD", "MEDIUM", 52.0, "MEDIUM", "REPORTED",
         13.0100, 80.2150, "Race Course Road, Guindy, Chennai", 65, 10, 4, {"GENERAL": 2},
         "Shallow water ponding across 400m of perimeter road. Traffic moving at walking pace with minor pedestrian diversions."),

        ("INC-DEMO-1017", "Mylapore Tank Square Waterlogging", "FLOOD", "LOW", 45.0, "LOW", "REPORTED",
         13.0330, 80.2690, "South Mada Street, Mylapore, Chennai", 50, 8, 2, {"GENERAL": 1},
         "Localized drainage clogging causing 0.3m water around historic temple tank perimeter. Pedestrian boardwalk active."),

        ("INC-DEMO-1018", "T. Nagar Ranganathan Street Canopy Wind Damage", "CYCLONE", "LOW", 40.0, "LOW", "REPORTED",
         13.0400, 80.2330, "Ranganathan Street Commercial Area, T. Nagar", 30, 4, 1, {"GENERAL": 1},
         "Advertising billboard torn down by cyclonic squall, obstructing one sidewalk lane. No structural collapse."),

        ("INC-DEMO-1019", "Chromepet GST Road Storm Drain Backup", "FLOOD", "LOW", 35.0, "LOW", "RESOLVED",
         12.9520, 80.1410, "GST Flyover Service Lane, Chromepet", 25, 3, 0, {"LOGISTICS": 1},
         "Service lane ponding cleared by municipal suction pump deployment. Normal traffic restored."),

        ("INC-DEMO-1020", "Kilpauk Garden Road Tree Branch Obstruction", "CYCLONE", "LOW", 30.0, "LOW", "CLOSED",
         13.0800, 80.2380, "Kilpauk Garden Road, Kilpauk, Chennai", 15, 1, 0, {"GENERAL": 1},
         "Large gulmohar branch felled across single traffic lane. Cleared by volunteer chainsaw team and road reopened.")
    ]

    total_evacuees_verified = 0
    incident_objs = []

    for code, title, dtype, prio_lvl, prio_score, sev_lvl, stat, lat, lng, addr, pop, vuln, inj, skills, desc in incidents_spec:
        # STRICT DEMOGRAPHIC CONSERVATION
        # people_affected == GEN + ACC + MED + MED_ACC
        # vulnerable_count == ACC + MED_ACC
        # injuries == MED + MED_ACC
        med_acc = min(vuln // 4, inj // 4)
        acc = max(0, vuln - med_acc)
        med = max(0, inj - med_acc)
        gen = max(0, pop - acc - med - med_acc)

        demo_partition = {
            "GEN": gen,
            "ACC": acc,
            "MED": med,
            "MED_ACC": med_acc
        }

        # Mathematical verification of conservation
        assert sum(demo_partition.values()) == pop, f"Conservation violation in {code}"
        total_evacuees_verified += pop

        geom_val = None if is_sqlite or ST_SetSRID is None else ST_SetSRID(ST_MakePoint(lng, lat), 4326)

        inc = Incident(
            incident_code=code,
            title=f"[DEMO] {title}",
            disaster_type=dtype,
            description=f"SYNTHETIC DEMONSTRATION INCIDENT: {desc}",
            status=stat,
            priority_level=prio_lvl,
            priority_score=prio_score,
            severity_level=sev_lvl,
            confidence_score=90.0,
            latitude=lat,
            longitude=lng,
            geom=geom_val,
            location_address=addr,
            people_affected=pop,
            injuries=inj,
            vulnerable_count=vuln,
            infrastructure_damage="Reported regional damage consistent with disaster intensity.",
            required_skills=skills,
            evacuation_demographics=demo_partition,
            ai_breakdown={
                "people_affected_bonus": min(40, pop // 5),
                "injuries_bonus": min(25, inj * 2),
                "vulnerable_bonus": min(20, vuln * 2),
                "infra_bonus": 15
            },
            cv_evidence_tags=["FLOODED_ROADS", "SUBMERGED_STRUCTURES"] if dtype == "FLOOD" else ["DEBRIS", "DAMAGED_ROOFING"]
        )
        db.add(inc)
        incident_objs.append(inc)

    db.commit()
    print(f"  -> Seeded 20 incidents (4 Critical, 6 High, 6 Medium, 4 Low).")
    print(f"  -> Verified strict demographic conservation across all 20 incidents ({total_evacuees_verified:,} total evacuees).")

    # -------------------------------------------------------------------------
    # 7. Road Blockages, Rescue Tasks, and Contextual Alerts
    # -------------------------------------------------------------------------
    print("\n[Step 7/8] Seeding road blockages, rescue tasks, and contextual alerts...")

    # Road Blockages
    blockages = [
        RoadBlockage(
            id="BLK_DEMO_01",
            title="Adyar River Bridge Transit Suspension",
            hazard_type="FLOOD",
            latitude=13.0050,
            longitude=80.2500,
            severity="CRITICAL",
            blockage_status="IMPASSABLE",
            delay_penalty_mins=0.0,
            source="GOVT",
            created_by_id=govt_admin.id
        ),
        RoadBlockage(
            id="BLK_DEMO_02",
            title="Mount-Poonamallee Arterial Deep Waterlogging",
            hazard_type="FLOOD",
            latitude=13.0200,
            longitude=80.1800,
            severity="HIGH",
            blockage_status="IMPASSABLE",
            delay_penalty_mins=0.0,
            source="FIELD_REPORT",
            created_by_id=govt_admin.id
        ),
        RoadBlockage(
            id="BLK_DEMO_03",
            title="GST Road Fallen Banyan Tree Obstruction",
            hazard_type="CYCLONE",
            latitude=12.9500,
            longitude=80.1400,
            severity="MEDIUM",
            blockage_status="DELAYED",
            delay_penalty_mins=35.0,
            source="FIELD_REPORT",
            created_by_id=govt_admin.id
        ),
        RoadBlockage(
            id="BLK_DEMO_04",
            title="Inner Ring Road Ponding near Velachery Bypass",
            hazard_type="FLOOD",
            latitude=12.9850,
            longitude=80.2100,
            severity="MEDIUM",
            blockage_status="DELAYED",
            delay_penalty_mins=20.0,
            source="FIELD_REPORT",
            created_by_id=govt_admin.id
        )
    ]
    db.add_all(blockages)

    # Active Rescue Tasks linking Incidents to Volunteers
    first_vols = [v[0] for v in volunteer_objs[:5]]
    rescue_tasks = [
        RescueTask(
            id="TASK_DEMO_01",
            incident_id=incident_objs[0].id,
            assigned_type="VOLUNTEER",
            assigned_id=first_vols[0].id,
            status="ASSIGNED"
        ),
        RescueTask(
            id="TASK_DEMO_02",
            incident_id=incident_objs[1].id,
            assigned_type="VOLUNTEER",
            assigned_id=first_vols[1].id,
            status="ACCEPTED"
        ),
        RescueTask(
            id="TASK_DEMO_03",
            incident_id=incident_objs[2].id,
            assigned_type="VOLUNTEER",
            assigned_id=first_vols[2].id,
            status="EN_ROUTE"
        ),
        RescueTask(
            id="TASK_DEMO_04",
            incident_id=incident_objs[3].id,
            assigned_type="VOLUNTEER",
            assigned_id=first_vols[3].id,
            status="ARRIVED"
        ),
        RescueTask(
            id="TASK_DEMO_05",
            incident_id=incident_objs[18].id,
            assigned_type="VOLUNTEER",
            assigned_id=first_vols[4].id,
            status="COMPLETED",
            completed_at=datetime.now(timezone.utc)
        )
    ]
    db.add_all(rescue_tasks)

    # Contextual Alerts grounded strictly in seeded conditions
    alerts = [
        Alert(
            id="ALT_DEMO_01",
            title="CRITICAL EVACUATION ORDER: ADYAR BASIN SECTOR 1 & 2",
            message="SYNTHETIC DEMO ALERT: Immediate evacuation mandatory for all residents within 500m of Adyar Riverbank. Open shelters: S-104 (Egmore) and S-145 (Adyar).",
            alert_type="EVACUATION",
            target_zone_lat=13.0060,
            target_zone_lng=80.2570,
            radius_km=4.5,
            created_by=govt_admin.id
        ),
        Alert(
            id="ALT_DEMO_02",
            title="FLASH FLOOD EMERGENCY WARNING: VELACHERY BYPASS",
            message="SYNTHETIC DEMO ALERT: Retention lake breach has caused severe street-level flooding exceeding 1.5m. Deploying inflatable motorboat teams.",
            alert_type="WARNING",
            target_zone_lat=12.9780,
            target_zone_lng=80.2180,
            radius_km=5.0,
            created_by=govt_admin.id
        ),
        Alert(
            id="ALT_DEMO_03",
            title="SHELTER CAPACITY WARNING: VELACHERY S-112 AT 92.5% OCCUPANCY",
            message="SYNTHETIC DEMO ALERT: Velachery S-112 is approaching maximum capacity (740/800 evacuees). Diverting secondary influx to Guindy S-115.",
            alert_type="SHELTER",
            target_zone_lat=12.9780,
            target_zone_lng=80.2180,
            radius_km=3.0,
            created_by=govt_admin.id
        ),
        Alert(
            id="ALT_DEMO_04",
            title="ROAD CLOSURE ADVISORY: ADYAR BRIDGE & MOUNT-POONAMALLEE IMPASSABLE",
            message="SYNTHETIC DEMO ALERT: Adyar River Bridge and Mount-Poonamallee roads are fully submerged and closed to non-emergency vehicular traffic.",
            alert_type="WARNING",
            target_zone_lat=13.0050,
            target_zone_lng=80.2500,
            radius_km=6.0,
            created_by=govt_admin.id
        ),
        Alert(
            id="ALT_DEMO_05",
            title="COASTAL SURGE & WIND HAZARD: ROYAPURAM TO ENNORE CORRIDOR",
            message="SYNTHETIC DEMO ALERT: Cyclone winds sustained at 115 km/h with 2.1m storm surge. Suspending light vehicle dispatch along North Beach Road.",
            alert_type="WARNING",
            target_zone_lat=13.1500,
            target_zone_lng=80.3000,
            radius_km=10.0,
            created_by=govt_admin.id
        ),
        Alert(
            id="ALT_DEMO_06",
            title="MEDICAL & WATER CONVOY DISPATCH ACTIVE FROM MGR CENTRAL DEPOT",
            message="SYNTHETIC DEMO ALERT: Heavy logistics trucks DEMO-VEH-01 and DEMO-VEH-02 dispatched with 15,000L drinking water and 400 trauma kits.",
            alert_type="GENERAL",
            target_zone_lat=13.0827,
            target_zone_lng=80.2707,
            radius_km=8.0,
            created_by=govt_admin.id
        )
    ]
    db.add_all(alerts)
    db.commit()
    print("  -> Seeded 4 road blockages, 5 rescue tasks, and 6 contextual alerts.")

    # -------------------------------------------------------------------------
    # 8. Curated Knowledge Base (RAG) & Canonical Simulation Scenarios
    # -------------------------------------------------------------------------
    print("\n[Step 8/8] Ingesting curated knowledge base and 7 canonical simulation scenarios...")

    # 8.1 Curated RAG Knowledge Base
    rag_doc_count = db.query(KnowledgeDocument).count()
    if rag_doc_count < 3:
        db.query(KnowledgeChunk).delete()
        db.query(KnowledgeDocument).delete()
        db.commit()

        documents_data = [
            {
                "title": "DIRS Curated Summary — NDMA Cyclone Risk Mitigation Framework",
                "org": "NDMA",
                "url": "https://ndma.gov.in/guidelines/cyclone",
                "type": "CURATED_SUMMARY",
                "disaster": "CYCLONE",
                "content": """# National Cyclone Risk Mitigation Framework

## Section 1: Pre-Evacuation Protocol

Upon issuance of Category 3 or Category 4 Cyclone warnings, local disaster management authorities must immediately establish pre-evacuation perimeters. Citizens residing in low-lying coastal sectors within 10km of forecasted landfall must be notified via multi-channel geofenced alerts. Evacuation centers and emergency shelters must be activated with minimum 3-day food rations, clean drinking water (min 15L per person/day), and essential medical trauma kits.

## Section 2: Wind and Storm Surge Safety

During peak cyclone landfall, ground rescue teams must suspend non-critical vehicle movement if wind velocities exceed 90 km/h. Structural shelters must have reinforced roofing and independent emergency power generators. Pre-position emergency clear-cut machinery to remove fallen trees and restore critical supply routes immediately following landfall."""
            },
            {
                "title": "DIRS Curated Summary — FEMA Flood Emergency SOP",
                "org": "FEMA",
                "url": "https://fema.gov/disaster/flood-sop",
                "type": "CURATED_SUMMARY",
                "disaster": "FLOOD",
                "content": """# Flood Emergency Response Standard Operating Procedures

## Section 1: Inundation Assessment and Boat Rescue

When floodwaters exceed 1.5 meters or river levels surpass critical flood stage, rapid water rescue teams equipped with inflatable motorboats and life jackets must be deployed. Emergency triage must prioritize marooned citizens on rooftops, vulnerable elderly populations, and injured victims. Ground personnel must monitor water level gauges hourly.

## Section 2: Emergency Shelter Sanitation and Triage

Flood evacuation shelters must maintain strict hygiene protocols to prevent waterborne disease outbreaks. Mandatory first aid kits, water purification tablets (minimum 5,000 tablets per 500 evacuees), and mobile sanitation units must be deployed to each active shelter site."""
            },
            {
                "title": "DIRS Curated Summary — WHO Emergency Medical Triage Guidelines",
                "org": "WHO",
                "url": "https://who.int/emergencies/first-aid-guidelines",
                "type": "CURATED_SUMMARY",
                "disaster": "GENERAL",
                "content": """# Emergency Medical Triage & First Aid Guidelines

## Section 1: Disaster Field Triage Protocol

First responders must utilize the START (Simple Triage and Rapid Treatment) algorithm to classify casualties: Red (Immediate life-threatening), Yellow (Delayed emergency), Green (Minor walking wounded), and Black (Deceased). Immediate field stabilization includes hemorrhage control with tourniquets, airway clearance, and shock prevention.

## Section 2: Mobile Field Clinic Operations

Mobile field clinics must carry trauma dressing kits, intravenous fluids, broad-spectrum antibiotics, and burn treatment supplies. High-priority casualty transfers to regional hospital facilities must be coordinated via central dispatch."""
            }
        ]

        total_chunks = 0
        for d in documents_data:
            v_hash = hashlib.sha256(d["content"].encode()).hexdigest()[:16]
            doc = KnowledgeDocument(
                title=d["title"],
                source_organization=d["org"],
                source_url=d["url"],
                document_type=d["type"],
                disaster_type=d["disaster"],
                version_hash=v_hash,
                metadata_info={
                    "language": "en",
                    "source_provenance": "CURATED_SUMMARY",
                    "publication_date": "2026-01-01",
                    "access_date": "2026-09-15",
                    "checksum": "NOT_AVAILABLE — SOURCE FILE NOT LOCALLY INGESTED",
                    "runtime_text_hash": v_hash,
                    "url_verification_status": "REFERENCE DOMAIN ONLY — UNVERIFIED"
                }
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            chunks_list = chunk_text_content(d["content"], chunk_size_tokens=500, chunk_overlap_tokens=80)
            for idx, c in enumerate(chunks_list):
                vec = EmbeddingProvider.encode(c["text_content"])
                sec_title = str(c.get("section_title", "General Guidance")).split("\n")[0].strip()[:100]
                chunk_entity = KnowledgeChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    section_title=sec_title,
                    text_content=c["text_content"],
                    token_count=c["token_count"],
                    embedding_vector=vec,
                    metadata_info={"section": sec_title, "source_document_id": doc.id}
                )
                db.add(chunk_entity)
                total_chunks += 1
            db.commit()
        print(f"  -> Curated knowledge summaries ingested for grounded retrieval (3 documents, {total_chunks} chunks).")
    else:
        print(f"  -> Curated knowledge summaries already active for grounded retrieval ({rag_doc_count} documents).")

    # 8.2 Canonical Simulation Scenarios A through G
    canonical_scenarios = [
        SimulationScenario(
            id="SCEN_DEMO_A_SURGE",
            name="Scenario A — Mass Influx Flood Surge [DEMO]",
            description="Simulated 40% surge in evacuees across coastal Adyar basin with secondary breached sector.",
            hazard_type="FLOOD",
            severity_multiplier=1.4,
            affected_area_multiplier=1.2,
            scenario_parameters_json={
                "new_incidents": [{
                    "id": "SIM_INC_SURGE_01",
                    "title": "Breached Riverbank Colony Secondary Surge",
                    "latitude": 13.0080,
                    "longitude": 80.2590,
                    "evacuees": 240,
                    "vulnerable_count": 48,
                    "injuries": 24,
                    "severity": "CRITICAL"
                }],
                "additional_blockages": [],
                "shelter_capacity_changes": {},
                "depot_supply_changes": {},
                "vehicle_availability_changes": [],
                "volunteer_availability_changes": []
            },
            seed=42,
            created_by_user_id=govt_admin.id
        ),
        SimulationScenario(
            id="SCEN_DEMO_B_ROAD_CLOSURE",
            name="Scenario B — Regional Arterial Road Closure [DEMO]",
            description="Simulated structural collapse of Adyar Bridge and secondary waterlogging cutting off South Chennai corridor.",
            hazard_type="FLOOD",
            severity_multiplier=1.0,
            affected_area_multiplier=1.0,
            scenario_parameters_json={
                "new_incidents": [],
                "additional_blockages": [{
                    "u": "HUB_GUINDY",
                    "v": "NODE_0012",
                    "status": "IMPASSABLE",
                    "delay_factor": 0.0,
                    "blockage_id": "SCEN_BLK_ADYAR_BRIDGE"
                }],
                "shelter_capacity_changes": {},
                "depot_supply_changes": {},
                "vehicle_availability_changes": [],
                "volunteer_availability_changes": []
            },
            seed=42,
            created_by_user_id=govt_admin.id
        ),
        SimulationScenario(
            id="SCEN_DEMO_C_SHELTER_LOSS",
            name="Scenario C — Critical Shelter Infiltration & Capacity Reduction [DEMO]",
            description="Simulated roof failure and basement flooding at Velachery S-112 shelter reducing usable capacity by 50%.",
            hazard_type="FLOOD",
            severity_multiplier=1.0,
            affected_area_multiplier=1.0,
            scenario_parameters_json={
                "new_incidents": [],
                "additional_blockages": [],
                "shelter_capacity_changes": {
                    "SHELTER_DEMO_003": 0.5,
                    "SHELTER_INT_002": 0.5
                },
                "depot_supply_changes": {},
                "vehicle_availability_changes": [],
                "volunteer_availability_changes": []
            },
            seed=42,
            created_by_user_id=govt_admin.id
        ),
        SimulationScenario(
            id="SCEN_DEMO_D_DEPOT_DEPLETION",
            name="Scenario D — Central Logistics Hub Clean Water Depletion [DEMO]",
            description="Simulated contamination of Central Logistics Hub municipal water main reducing available water supplies by 70%.",
            hazard_type="FLOOD",
            severity_multiplier=1.0,
            affected_area_multiplier=1.0,
            scenario_parameters_json={
                "new_incidents": [],
                "additional_blockages": [],
                "shelter_capacity_changes": {},
                "depot_supply_changes": {
                    "DEPOT_CENTRAL": {"WATER": 0.3},
                    "DEPOT_INT_001": {"WATER": 0.3}
                },
                "vehicle_availability_changes": [],
                "volunteer_availability_changes": []
            },
            seed=42,
            created_by_user_id=govt_admin.id
        ),
        SimulationScenario(
            id="SCEN_DEMO_E_VEHICLE_LOSS",
            name="Scenario E — Heavy Transport Fleet Breakdown [DEMO]",
            description="Simulated mechanical immobilizer failure and water ingress disabling 2 heavy transport trucks.",
            hazard_type="FLOOD",
            severity_multiplier=1.0,
            affected_area_multiplier=1.0,
            scenario_parameters_json={
                "new_incidents": [],
                "additional_blockages": [],
                "shelter_capacity_changes": {},
                "depot_supply_changes": {},
                "vehicle_availability_changes": ["DEMO-VEH-01", "DEMO-VEH-05", "VEH_INT_002"],
                "volunteer_availability_changes": []
            },
            seed=42,
            created_by_user_id=govt_admin.id
        ),
        SimulationScenario(
            id="SCEN_DEMO_F_VOLUNTEER_SHORTFALL",
            name="Scenario F — Monsoon Night Shift Volunteer Exhaustion [DEMO]",
            description="Simulated 40% reduction in active responder workforce due to transit cutoffs and extreme night fatigue.",
            hazard_type="CYCLONE",
            severity_multiplier=1.0,
            affected_area_multiplier=1.0,
            scenario_parameters_json={
                "new_incidents": [],
                "additional_blockages": [],
                "shelter_capacity_changes": {},
                "depot_supply_changes": {},
                "vehicle_availability_changes": [],
                "volunteer_availability_changes": [],
                "volunteer_reduction_pct": 40.0
            },
            seed=42,
            created_by_user_id=govt_admin.id
        ),
        SimulationScenario(
            id="SCEN_DEMO_G_CASCADING_CRISIS",
            name="Scenario G — Cyclone Vardah Cascading Escalation [DEMO]",
            description="Simulated compound crisis combining landfall surge (+30% demand), arterial road severance, vehicle loss, and shelter capacity drop.",
            hazard_type="CYCLONE",
            severity_multiplier=1.3,
            affected_area_multiplier=1.2,
            scenario_parameters_json={
                "new_incidents": [{
                    "id": "SIM_INC_CASCADING_01",
                    "title": "Royapuram Coastal Embankment Washout",
                    "latitude": 13.1150,
                    "longitude": 80.2980,
                    "evacuees": 180,
                    "vulnerable_count": 36,
                    "injuries": 18,
                    "severity": "CRITICAL"
                }],
                "additional_blockages": [{
                    "u": "HUB_CENTRAL",
                    "v": "NODE_0020",
                    "status": "IMPASSABLE",
                    "delay_factor": 0.0,
                    "blockage_id": "SCEN_BLK_CASCADING_CUTOFF"
                }],
                "shelter_capacity_changes": {
                    "SHELTER_DEMO_003": 0.5,
                    "SHELTER_INT_002": 0.5
                },
                "depot_supply_changes": {
                    "DEPOT_CENTRAL": {"WATER": 0.5, "MEDICAL_KITS": 0.5}
                },
                "vehicle_availability_changes": ["DEMO-VEH-02", "VEH_INT_002"],
                "volunteer_availability_changes": [],
                "volunteer_reduction_pct": 30.0
            },
            seed=42,
            created_by_user_id=govt_admin.id
        )
    ]

    for sc in canonical_scenarios:
        existing = db.query(SimulationScenario).filter(SimulationScenario.id == sc.id).first()
        if existing:
            db.delete(existing)
            db.commit()
        db.add(sc)
    db.commit()
    print("  -> Seeded 7 canonical simulation scenarios (Archetypes A through G).")

    # -------------------------------------------------------------------------
    # Verification & Final Integrity Audit
    # -------------------------------------------------------------------------
    print("\n================================================================================")
    print("DATA POPULATION INTEGRITY AUDIT")
    print("================================================================================")

    u_cnt = db.query(User).count()
    inc_cnt = db.query(Incident).count()
    sh_cnt = db.query(Shelter).count()
    res_cnt = db.query(Resource).count()
    veh_cnt = db.query(Vehicle).count()
    vol_cnt = db.query(VolunteerProfile).count()
    alt_cnt = db.query(Alert).count()
    blk_cnt = db.query(RoadBlockage).count()
    tsk_cnt = db.query(RescueTask).count()
    scen_cnt = db.query(SimulationScenario).count()
    doc_cnt = db.query(KnowledgeDocument).count()

    print(f"Users (Total):              {u_cnt}")
    print(f"Volunteers (Profiles):      {vol_cnt}")
    print(f"Incidents (Total):          {inc_cnt}")
    print(f"Shelters (Facilities):      {sh_cnt}")
    print(f"Resources (Inventories):    {res_cnt}")
    print(f"Vehicles (Fleet):           {veh_cnt}")
    print(f"Road Blockages:             {blk_cnt}")
    print(f"Rescue Tasks:               {tsk_cnt}")
    print(f"Contextual Alerts:          {alt_cnt}")
    print(f"Knowledge Documents (RAG):  {doc_cnt}")
    print(f"Simulation Scenarios:       {scen_cnt}")

    # Check demographic conservation across all incidents in DB
    all_incs = db.query(Incident).all()
    demo_violations = 0
    for inc in all_incs:
        if inc.evacuation_demographics:
            tot = sum(inc.evacuation_demographics.values())
            if tot != inc.people_affected:
                print(f"  [ERROR] Conservation violation in incident {inc.incident_code}: sum={tot} != people_affected={inc.people_affected}")
                demo_violations += 1
    if demo_violations == 0:
        print("\nDemographic Conservation Invariant: STRICT PASS (0 violations across all incidents).")
    else:
        print(f"\nDemographic Conservation Invariant: FAIL ({demo_violations} violations).")

    # Check shelter occupancy
    all_shelters = db.query(Shelter).all()
    shelter_violations = 0
    for s in all_shelters:
        if s.current_occupancy > s.total_capacity:
            print(f"  [ERROR] Shelter capacity violation in {s.name}: occ={s.current_occupancy} > cap={s.total_capacity}")
            shelter_violations += 1
    if shelter_violations == 0:
        print("Shelter Capacity Bounds:            STRICT PASS (0 occupancies exceed capacity).")

    print("================================================================================\n")
    return {
        "users": u_cnt,
        "volunteers": vol_cnt,
        "incidents": inc_cnt,
        "shelters": sh_cnt,
        "resources": res_cnt,
        "vehicles": veh_cnt,
        "alerts": alt_cnt,
        "scenarios": scen_cnt,
        "knowledge_docs": doc_cnt
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DIRS Comprehensive Operational Demo Seeder")
    parser.add_argument("--sqlite", type=str, default=None, help="Path to SQLite DB file (e.g. dirs_dev.db)")
    parser.add_argument("--db-url", type=str, default=None, help="Custom database connection URL")
    args = parser.parse_args()

    custom_url = None
    if args.sqlite:
        sqlite_path = os.path.abspath(args.sqlite)
        custom_url = f"sqlite:///{sqlite_path}"
    elif args.db_url:
        custom_url = args.db_url

    eng, session = get_db_session(custom_url)
    try:
        seed_operational_demo(session, eng)
    finally:
        session.close()
