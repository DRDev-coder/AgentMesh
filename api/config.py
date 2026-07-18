from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _boolean(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _integer(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    database_url: str
    redis_url: str
    auth_mode: str
    supabase_url: str
    supabase_jwt_audience: str
    cors_origins: tuple[str, ...]
    free_decisions_per_month: int
    document_max_bytes: int
    object_storage_backend: str
    object_storage_path: Path
    s3_endpoint_url: str
    s3_region: str
    s3_bucket: str
    s3_access_key_id: str
    s3_secret_access_key: str
    api_key_pepper: str
    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_webhook_secret: str
    razorpay_plan_id: str
    razorpay_subscription_total_count: int
    razorpay_base_url: str
    public_app_url: str
    saas_enabled: bool
    tasks_eager: bool
    webhook_encryption_key: str
    public_rate_limit_per_minute: int
    resend_api_key: str
    resend_from: str
    overage_unit_price_paise: int
    provider_cost_cap_cents: int
    estimated_cost_per_decision_millicents: int
    malware_scan_url: str
    malware_scan_api_key: str

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("APP_ENV", "development").strip().lower()
        default_database = "sqlite+pysqlite:///state/agentmesh-saas.db"
        settings = cls(
            environment=environment,
            database_url=os.getenv("DATABASE_URL", default_database).strip(),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0").strip(),
            auth_mode=os.getenv("AUTH_MODE", "development").strip().lower(),
            supabase_url=os.getenv("SUPABASE_URL", "").strip().rstrip("/"),
            supabase_jwt_audience=os.getenv(
                "SUPABASE_JWT_AUDIENCE", "authenticated"
            ).strip(),
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv(
                    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
                ).split(",")
                if origin.strip()
            ),
            free_decisions_per_month=max(
                0, _integer("FREE_DECISIONS_PER_MONTH", 500)
            ),
            document_max_bytes=max(
                1, _integer("DOCUMENT_MAX_BYTES", 25 * 1024 * 1024)
            ),
            object_storage_backend=os.getenv(
                "OBJECT_STORAGE_BACKEND", "local"
            ).strip().lower(),
            object_storage_path=Path(
                os.getenv("OBJECT_STORAGE_PATH", "state/documents")
            ),
            s3_endpoint_url=os.getenv("S3_ENDPOINT_URL", "").strip(),
            s3_region=os.getenv("S3_REGION", "auto").strip(),
            s3_bucket=os.getenv("S3_BUCKET", "agentmesh-documents").strip(),
            s3_access_key_id=os.getenv("S3_ACCESS_KEY_ID", "").strip(),
            s3_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY", "").strip(),
            api_key_pepper=os.getenv(
                "API_KEY_PEPPER", "development-only-agentmesh-pepper"
            ),
            razorpay_key_id=os.getenv("RAZORPAY_KEY_ID", "").strip(),
            razorpay_key_secret=os.getenv("RAZORPAY_KEY_SECRET", "").strip(),
            razorpay_webhook_secret=os.getenv(
                "RAZORPAY_WEBHOOK_SECRET", ""
            ).strip(),
            razorpay_plan_id=os.getenv("RAZORPAY_PLAN_ID", "").strip(),
            razorpay_subscription_total_count=max(
                1, _integer("RAZORPAY_SUBSCRIPTION_TOTAL_COUNT", 120)
            ),
            razorpay_base_url=os.getenv(
                "RAZORPAY_BASE_URL", "https://api.razorpay.com/v1"
            ).strip().rstrip("/"),
            public_app_url=os.getenv(
                "PUBLIC_APP_URL", "http://localhost:3000"
            ).strip().rstrip("/"),
            saas_enabled=_boolean("SAAS_ENABLED", True),
            tasks_eager=_boolean("TASKS_EAGER", environment in {"development", "test"}),
            webhook_encryption_key=os.getenv(
                "WEBHOOK_ENCRYPTION_KEY", "development-webhook-key"
            ),
            public_rate_limit_per_minute=max(
                1, _integer("PUBLIC_RATE_LIMIT_PER_MINUTE", 60)
            ),
            resend_api_key=(
                os.getenv("RESEND_API_KEY")
                or os.getenv("EMAIL_PROVIDER_API_KEY", "")
            ).strip(),
            resend_from=(
                os.getenv("RESEND_FROM")
                or os.getenv("EMAIL_FROM", "AgentMesh <onboarding@resend.dev>")
            ).strip(),
            overage_unit_price_paise=max(
                0, _integer("OVERAGE_UNIT_PRICE_PAISE", 0)
            ),
            provider_cost_cap_cents=max(0, _integer("PROVIDER_COST_CAP_CENTS", 0)),
            estimated_cost_per_decision_millicents=max(
                0, _integer("ESTIMATED_COST_PER_DECISION_MILLICENTS", 0)
            ),
            malware_scan_url=os.getenv("MALWARE_SCAN_URL", "").strip(),
            malware_scan_api_key=os.getenv("MALWARE_SCAN_API_KEY", "").strip(),
        )
        settings.validate()
        return settings

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    def validate(self) -> None:
        if self.environment not in {"development", "test", "staging", "production"}:
            raise RuntimeError("APP_ENV must be development, test, staging, or production")
        if self.auth_mode not in {"development", "supabase"}:
            raise RuntimeError("AUTH_MODE must be development or supabase")
        if self.object_storage_backend not in {"local", "s3"}:
            raise RuntimeError("OBJECT_STORAGE_BACKEND must be local or s3")
        if self.auth_mode == "supabase" and not self.supabase_url:
            raise RuntimeError("SUPABASE_URL is required when AUTH_MODE=supabase")
        if self.is_production:
            if not self.database_url.startswith("postgresql"):
                raise RuntimeError("Production requires a PostgreSQL DATABASE_URL")
            if "localhost" in self.redis_url or not self.redis_url.startswith(
                ("redis://", "rediss://")
            ):
                raise RuntimeError("Production requires a managed Redis URL")
            if self.auth_mode != "supabase":
                raise RuntimeError("Production requires AUTH_MODE=supabase")
            if not self.supabase_url.startswith("https://"):
                raise RuntimeError("Production requires an HTTPS SUPABASE_URL")
            if len(self.api_key_pepper) < 32 or self.api_key_pepper == "development-only-agentmesh-pepper":
                raise RuntimeError("Production requires a strong API_KEY_PEPPER")
            if len(self.webhook_encryption_key) < 32 or self.webhook_encryption_key == "development-webhook-key":
                raise RuntimeError("Production requires WEBHOOK_ENCRYPTION_KEY")
            if self.object_storage_backend != "s3":
                raise RuntimeError("Production requires private S3-compatible storage")
            if not all(
                [self.s3_bucket, self.s3_access_key_id, self.s3_secret_access_key]
            ):
                raise RuntimeError("Production requires private object storage credentials")
            if not self.public_app_url.startswith("https://"):
                raise RuntimeError("Production requires an HTTPS PUBLIC_APP_URL")
            if not self.cors_origins or any(
                origin == "*" or not origin.startswith("https://")
                for origin in self.cors_origins
            ):
                raise RuntimeError("Production requires exact HTTPS CORS_ORIGINS")
            if not all(
                [
                    self.razorpay_key_id,
                    self.razorpay_key_secret,
                    self.razorpay_webhook_secret,
                    self.razorpay_plan_id,
                ]
            ):
                raise RuntimeError("Production requires Razorpay billing configuration")
            if not self.resend_api_key or not self.resend_from:
                raise RuntimeError("Production requires Resend email configuration")
            if not self.malware_scan_url or not self.malware_scan_api_key:
                raise RuntimeError("Production requires a malware scanning provider")
            if self.overage_unit_price_paise <= 0:
                raise RuntimeError("Production requires OVERAGE_UNIT_PRICE_PAISE")
            if self.provider_cost_cap_cents <= 0:
                raise RuntimeError("Production requires PROVIDER_COST_CAP_CENTS")
            if self.estimated_cost_per_decision_millicents <= 0:
                raise RuntimeError(
                    "Production requires ESTIMATED_COST_PER_DECISION_MILLICENTS"
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
