from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
import socket
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse

load_dotenv()

class Settings(BaseSettings):
    _redis_fallback_logged: bool = False

    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    PROMPT_DIR: str = os.path.join(BASE_DIR, "app", "prompts")

    # Database config — reads DB_* env vars (set in .env / .env.gcp)
    DB_HOST: str = Field("localhost", alias="DB_HOST")
    DB_PORT: int = Field(3306, alias="DB_PORT")
    DB_USER: str = Field("niyamtek_user", alias="DB_USER")
    DB_PASSWORD: str = Field("", alias="DB_PASSWORD")
    DB_NAME: str = Field("matex_db", alias="DB_NAME")
    # Optional override: set SQLALCHEMY_DATABASE_URI to skip per-field building
    SQLALCHEMY_DATABASE_URI: str | None = Field(None, alias="SQLALCHEMY_DATABASE_URI")

    @property
    def DATABASE_URL(self) -> str:
        if self.SQLALCHEMY_DATABASE_URI:
            return self.SQLALCHEMY_DATABASE_URI
        from urllib.parse import quote_plus
        escaped_password = quote_plus(self.DB_PASSWORD)
        return f"mysql+pymysql://{self.DB_USER}:{escaped_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # ── Google Cloud Storage (replaces AWS S3) ───────────────────────
    GCS_BUCKET_NAME: str = Field(..., alias="GCS_BUCKET_NAME")
    GCS_LOCATION: str = Field("asia-south1", alias="GCS_LOCATION")
    GCS_BASE_URL: str = Field("", alias="GCS_BASE_URL")

    # Backend base URL used to construct file-serve URLs as fallback for signed URLs
    # e.g. https://api.niyamtek.com  (no trailing slash)
    BACKEND_BASE_URL: str = Field("", alias="BACKEND_BASE_URL")

    # Backward-compat aliases so existing service code works without changes
    @property
    def S3_BUCKET_NAME(self) -> str:
        return self.GCS_BUCKET_NAME

    @property
    def S3_BASE_URL(self) -> str:
        return self.GCS_BASE_URL

    # Template URL settings (used by template_service.py)
    TEMPLATE_URL_MODE: str = Field("presigned", alias="TEMPLATE_URL_MODE")
    TEMPLATE_PRESIGNED_EXPIRY_SECONDS: int = Field(3600, alias="TEMPLATE_PRESIGNED_EXPIRY_SECONDS")

    GEMINI_API_KEY: str = Field(..., alias="GEMINI_API_KEY")

    # ── Google Cloud settings ────────────────────────────────────────
    # GOOGLE_APPLICATION_CREDENTIALS is optional on GCP VMs — the VM's
    # attached service account is picked up automatically via ADC.
    GOOGLE_APPLICATION_CREDENTIALS: str | None = Field(None, alias="GOOGLE_APPLICATION_CREDENTIALS")
    GOOGLE_PROJECT_ID: str = Field(..., alias="GOOGLE_PROJECT_ID")
    GOOGLE_LOCATION: str = Field(..., alias="GOOGLE_LOCATION")
    GOOGLE_PROCESSOR_ID: str = Field(..., alias="GOOGLE_PROCESSOR_ID")
    TMP_DIR: str = Field("./tmp", alias="TMP_DIR")

    POPPLER_PATH: str = Field(..., alias="POPPLER_PATH")
    LIBREOFFICE_PATH: str = Field(..., env="LIBREOFFICE_PATH")

    JWT_SECRET_KEY: str = Field(..., alias="JWT_SECRET_KEY")

    REDIS_HOST: str = Field("redis", alias="REDIS_HOST")
    REDIS_PORT: int = Field(6379, alias="REDIS_PORT")
    REDIS_DB: int = Field(0, alias="REDIS_DB")
    REDIS_URL: str | None = Field(None, alias="REDIS_URL")
    CELERY_BROKER_URL: str | None = Field(None, alias="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str | None = Field(None, alias="CELERY_RESULT_BACKEND")

    def _is_host_resolvable(self, host: str) -> bool:
        try:
            socket.getaddrinfo(host, None)
            return True
        except Exception:
            return False

    def _normalize_redis_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme != "redis":
            return url

        host = parsed.hostname
        if not host:
            return url

        if host == "redis" and not self._is_host_resolvable(host):
            netloc = parsed.netloc.replace("redis", "localhost", 1)
            fallback_url = urlunparse(parsed._replace(netloc=netloc))
            if not self._redis_fallback_logged:
                print(f"INFO: Redis host 'redis' is not resolvable here. Falling back to '{fallback_url}'.")
                self._redis_fallback_logged = True
            return fallback_url
        return url

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self._normalize_redis_url(self.REDIS_URL)
        return self._normalize_redis_url(
            f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        )

    @property
    def celery_broker_url(self) -> str:
        if self.CELERY_BROKER_URL:
            return self._normalize_redis_url(self.CELERY_BROKER_URL)
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        if self.CELERY_RESULT_BACKEND:
            return self._normalize_redis_url(self.CELERY_RESULT_BACKEND)
        return self.redis_url

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()  # pyright: ignore[reportCallIssue]

os.makedirs(settings.TMP_DIR, exist_ok=True)
