from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Standard synchronous engine for FastAPI / PostGIS ORM
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
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

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
