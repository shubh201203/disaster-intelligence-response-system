import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "DIRS — Disaster Intelligence and Response System"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Security
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dirs_jwt_secret_key_super_secure_change_me_in_production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    BENEFICIARY_HASH_SALT: str = os.getenv("BENEFICIARY_HASH_SALT", "")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://dirs_user:dirs_password_secure@localhost:5432/dirs_db"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Uploads & Request Limits
    MEDIA_UPLOAD_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads"))
    MAX_REQUEST_BODY_BYTES: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(10 * 1024 * 1024)))  # 10 MB default
    
    model_config = ConfigDict(case_sensitive=True)

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env = (self.ENVIRONMENT or "").strip().lower()
        if env in ("production", "staging"):
            default_key = "dirs_jwt_secret_key_super_secure_change_me_in_production"
            if not self.SECRET_KEY or self.SECRET_KEY == default_key or len(self.SECRET_KEY) < 32:
                raise RuntimeError(
                    f"FATAL: In '{env}' environment, SECRET_KEY must be explicitly configured "
                    "with a secure string of at least 32 characters."
                )
            if not self.BENEFICIARY_HASH_SALT or len(self.BENEFICIARY_HASH_SALT) < 16:
                raise RuntimeError(
                    f"FATAL: In '{env}' environment, BENEFICIARY_HASH_SALT must be configured "
                    "with a cryptographic salt of at least 16 characters."
                )
        return self

settings = Settings()
