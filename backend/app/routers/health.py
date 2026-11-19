from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import settings
import redis

router = APIRouter(tags=["Health"])

@router.get("/health")
def check_health(db: Session = Depends(get_db)):
    health_status = {
        "status": "ok",
        "database": "disconnected",
        "redis": "disconnected",
        "ai_engine": "ready"
    }

    # 1. Check PostgreSQL connection
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # 2. Check Redis connection
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1.0)
        if r.ping():
            health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status
