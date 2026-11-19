import os
import sys
import pytest

# 1. Set test database environment variable FIRST
os.environ["DATABASE_URL"] = "sqlite:///./test_dirs.db"
os.environ.setdefault("BENEFICIARY_HASH_SALT", "test_dirs_recovery_salt_k9x2m8q4_configured_secure")

# 2. Suppress GeoAlchemy DDL event listeners for SQLite test environment
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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from app.database import Base, engine, get_db
from app.main import app
from sqlalchemy.orm import sessionmaker

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
    if os.path.exists("./test_dirs.db"):
        try:
            os.remove("./test_dirs.db")
        except Exception:
            pass

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
