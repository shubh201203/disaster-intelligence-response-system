from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[str],
        action: str,
        target_entity: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            target_entity=target_entity,
            details=details or {},
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
