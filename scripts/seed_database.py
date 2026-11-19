import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, CitizenProfile, VolunteerProfile, NGOProfile, Incident, Shelter, Resource, Alert
from app.core.security import get_password_hash
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Clear existing seed data if present
        db.query(Alert).delete()
        db.query(Resource).delete()
        db.query(Shelter).delete()
        db.query(Incident).delete()
        db.query(CitizenProfile).delete()
        db.query(VolunteerProfile).delete()
        db.query(NGOProfile).delete()
        db.query(User).delete()
        db.commit()

        print("Creating default role accounts...")
        # 2. Users
        pwd = get_password_hash("Admin123!")
        govt_user = User(email="admin@dirs.gov", hashed_password=pwd, full_name="Command Admin Officer", role="GOVT", phone="+1-800-DISASTER")
        
        citizen_pwd = get_password_hash("Citizen123!")
        citizen_user = User(email="citizen@dirs.org", hashed_password=citizen_pwd, full_name="Rahul Sharma", role="CITIZEN", phone="+91-9876543210")
        
        vol_pwd = get_password_hash("Volunteer123!")
        vol_user = User(email="volunteer@dirs.org", hashed_password=vol_pwd, full_name="Priya Patel", role="VOLUNTEER", phone="+91-9876543211")
        
        ngo_pwd = get_password_hash("Ngo123!")
        ngo_user = User(email="ngo@dirs.org", hashed_password=ngo_pwd, full_name="Global Relief Foundation", role="NGO", phone="+91-9876543212")

        db.add_all([govt_user, citizen_user, vol_user, ngo_user])
        db.commit()

        # Profiles
        db.add(CitizenProfile(user_id=citizen_user.id, emergency_contact_name="Sunita Sharma", emergency_contact_phone="+91-9876500000", address="Riverfront Colony, District A", latitude=13.0827, longitude=80.2707))
        db.add(VolunteerProfile(user_id=vol_user.id, skills=["First Aid", "Water Rescue", "CPR"], experience_years=4, vehicle_type="4x4 Rescue Truck", medical_certified=True, verification_status="VERIFIED", is_available=True, current_lat=13.0850, current_lng=80.2750))
        db.add(NGOProfile(user_id=ngo_user.id, org_name="Global Relief Foundation", registration_no="NGO-2024-8891", contact_person="Priya Singh", address="Main Relief Logistics Hub", verified=True))
        db.commit()

        print("Seeding emergency shelters...")
        # 3. Shelters
        is_sqlite = engine.dialect.name == "sqlite"
        geom1 = None if is_sqlite else ST_SetSRID(ST_MakePoint(80.2780, 13.0870), 4326)
        geom2 = None if is_sqlite else ST_SetSRID(ST_MakePoint(80.2650, 13.0950), 4326)
        geom3 = None if is_sqlite else ST_SetSRID(ST_MakePoint(80.2707, 13.0827), 4326)

        s1 = Shelter(
            name="District Central Emergency Shelter S-104",
            address="Community Complex, Sector 4, District A",
            total_capacity=500,
            current_occupancy=310,
            latitude=13.0870,
            longitude=80.2780,
            geom=geom1,
            has_medical=True,
            has_food=True,
            has_water=True,
            disaster_risk_level="LOW",
            status="OPEN"
        )
        s2 = Shelter(
            name="North High School Safe Haven S-108",
            address="12 High School Road, Sector 2",
            total_capacity=300,
            current_occupancy=90,
            latitude=13.0950,
            longitude=80.2650,
            geom=geom2,
            has_medical=True,
            has_food=True,
            has_water=True,
            disaster_risk_level="LOW",
            status="OPEN"
        )
        db.add_all([s1, s2])
        db.commit()

        print("Seeding active incidents...")
        # 4. Incidents
        i1 = Incident(
            incident_code="INC-2026-1024",
            title="Severe Flash Flooding near Riverfront Colony",
            disaster_type="FLOOD",
            description="Rapid rise in water level due to overflow from dam release. Multiple households submerged.",
            status="VERIFIED",
            priority_level="CRITICAL",
            priority_score=94.0,
            severity_level="CRITICAL",
            confidence_score=92.0,
            latitude=13.0827,
            longitude=80.2707,
            geom=geom3,
            location_address="Riverfront Colony, District A",
            people_affected=45,
            injuries=12,
            vulnerable_count=8,
            infrastructure_damage="Bridge partially damaged, power lines down",
            ai_breakdown={"people_affected_bonus": 25, "injuries_bonus": 20, "vulnerable_bonus": 15, "infra_bonus": 20},
            cv_evidence_tags=["FLOODED_ROADS", "BUILDING_COLLAPSE"]
        )
        geom4 = None if is_sqlite else ST_SetSRID(ST_MakePoint(80.2500, 13.1100), 4326)

        i2 = Incident(
            incident_code="INC-2026-1025",
            title="Landslide Blocking Highway 9",
            disaster_type="LANDSLIDE",
            description="Debris and large boulders blocking emergency vehicle transit.",
            status="REPORTED",
            priority_level="HIGH",
            priority_score=76.0,
            severity_level="HIGH",
            confidence_score=85.0,
            latitude=13.1100,
            longitude=80.2500,
            geom=geom4,
            location_address="Highway 9, North Sector",
            people_affected=15,
            injuries=2,
            vulnerable_count=1,
            infrastructure_damage="Road completely blocked",
            ai_breakdown={"people_affected_bonus": 15, "injuries_bonus": 10, "infra_bonus": 25},
            cv_evidence_tags=["DEBRIS"]
        )
        db.add_all([i1, i2])
        db.commit()

        print("Seeding relief resources...")
        # 5. Resources
        r1 = Resource(owner_type="NGO", owner_id=ngo_user.id, category="FOOD", resource_name="Ready-to-Eat Food Packets", total_quantity=2000, available_quantity=1650, unit="packets", location_lat=13.0850, location_lng=80.2750)
        r2 = Resource(owner_type="NGO", owner_id=ngo_user.id, category="WATER", resource_name="Drinking Water Bottles (2L)", total_quantity=5000, available_quantity=4100, unit="bottles", location_lat=13.0850, location_lng=80.2750)
        r3 = Resource(owner_type="GOVT", owner_id=govt_user.id, category="MEDICINE", resource_name="Emergency First Aid Kits", total_quantity=400, available_quantity=320, unit="kits", location_lat=13.0870, location_lng=80.2780)
        db.add_all([r1, r2, r3])

        print("Seeding alerts...")
        # 6. Alerts
        alt = Alert(
            title="FLASH FLOOD EVACUATION WARNING",
            message="Immediate evacuation ordered for residents within 500m of Riverfront Colony due to water rise.",
            alert_type="EVACUATION",
            target_zone_lat=13.0827,
            target_zone_lng=80.2707,
            radius_km=5.0,
            created_by=govt_user.id
        )
        db.add(alt)

        db.commit()
        print("Database seeded successfully with realistic disaster demo data!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
