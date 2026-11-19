import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def hash_beneficiary_id(raw_id: str) -> str:
    """
    Computes a cryptographic salted SHA-256 pseudonymized hash of sensitive national/household beneficiary ID.
    Requires settings.BENEFICIARY_HASH_SALT to be explicitly configured.
    Fails closed if the salt is absent or unconfigured. Insecure fallbacks are strictly disabled.
    """
    if not raw_id:
        return ""
    salt = getattr(settings, "BENEFICIARY_HASH_SALT", "") or os.getenv("BENEFICIARY_HASH_SALT", "")
    if not salt or not str(salt).strip():
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: BENEFICIARY_HASH_SALT is not configured. "
            "Beneficiary pseudonymization requires an explicitly configured secret salt. "
            "Insecure default fallbacks are disabled."
        )
    salted_input = f"{str(salt).strip()}:{raw_id.strip()}:{str(salt).strip()}"
    return hashlib.sha256(salted_input.encode("utf-8")).hexdigest()

def mask_person_name(name: str) -> str:
    """
    Masks person name for public presentation (e.g. 'Ramesh Kumar' -> 'R****h K***r').
    """
    if not name:
        return ""
    parts = name.strip().split()
    masked = []
    for p in parts:
        if len(p) <= 2:
            masked.append(p[0] + "*")
        else:
            masked.append(p[0] + "*" * (len(p) - 2) + p[-1])
    return " ".join(masked)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
