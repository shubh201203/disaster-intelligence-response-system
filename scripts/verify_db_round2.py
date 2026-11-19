import os
import sys
import alembic.config
import alembic.command
from sqlalchemy import text, inspect

# Add workspace and backend to path
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))
sys.path.insert(0, os.getcwd())
from app.database import engine

def verify_db():
    print("=== ALEMBIC CURRENT ===")
    alembic_cfg = alembic.config.Config(os.path.join(os.getcwd(), "backend", "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(os.getcwd(), "backend", "alembic"))
    alembic.command.current(alembic_cfg)

    with engine.connect() as conn:
        insp = inspect(conn)
        tables = insp.get_table_names()
        print(f"Total tables detected by inspector: {len(tables)}")

        res = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")).scalar()
        print(f"Base tables in public schema: {res}")

        # Check recovery_projects.priority_score
        score_not_null = conn.execute(text("SELECT count(*) FROM recovery_projects WHERE priority_score IS NOT NULL")).scalar()
        print(f"recovery_projects with non-null priority_score: {score_not_null}")

        # Check alembic_version
        ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print(f"Alembic version in DB: {ver}")

if __name__ == "__main__":
    verify_db()
