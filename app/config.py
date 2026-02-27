import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _resolve_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    if environment == "development":
        return "postgresql+psycopg://localhost:5434/dotmac_ecm"

    raise ValueError(
        "DATABASE_URL is not set. Set DATABASE_URL for non-development "
        "environments or set ENVIRONMENT=development for local defaults."
    )


@dataclass(frozen=True)
class Settings:
    database_url: str = _resolve_database_url()
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "5"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    db_pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    db_pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    # Avatar settings
    avatar_upload_dir: str = os.getenv("AVATAR_UPLOAD_DIR", "static/avatars")
    avatar_max_size_bytes: int = int(
        os.getenv("AVATAR_MAX_SIZE_BYTES", str(2 * 1024 * 1024))
    )  # 2MB
    avatar_allowed_types: str = os.getenv(
        "AVATAR_ALLOWED_TYPES", "image/jpeg,image/png,image/gif,image/webp"
    )
    avatar_url_prefix: str = os.getenv("AVATAR_URL_PREFIX", "/static/avatars")

    # S3 / MinIO settings
    s3_endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "")
    s3_access_key: str = os.getenv("S3_ACCESS_KEY", "")
    s3_secret_key: str = os.getenv("S3_SECRET_KEY", "")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "ecm-documents")
    s3_region: str = os.getenv("S3_REGION", "us-east-1")
    s3_presigned_url_expiry: int = int(os.getenv("S3_PRESIGNED_URL_EXPIRY", "3600"))

    # Branding
    brand_name: str = os.getenv("BRAND_NAME", "DotMac ECM")
    brand_tagline: str = os.getenv("BRAND_TAGLINE", "Electronic Content Management")
    brand_logo_url: str | None = os.getenv("BRAND_LOGO_URL") or None


settings = Settings()
