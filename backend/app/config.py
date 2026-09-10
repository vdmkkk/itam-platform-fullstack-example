from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (or a local `.env`)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://example:example@localhost:5432/example_backend"

    # --- identity bridge to the course platform ---
    platform_api_url: str = "https://courses.salut.uno"
    platform_service_key: str = ""
    backend_slug: str = "frontend-itam"

    # --- public address ---
    # The edge proxy strips /example-backend/<slug> before the request reaches
    # us, so the docs must re-advertise it. Empty when running locally.
    root_path: str = ""
    # Absolute public URL, used in the docs and as the OpenAPI server.
    public_base_url: str = ""

    # --- admin API (X-Admin-Token). Empty disables the admin endpoints. ---
    admin_token: str = ""

    # --- caching and limits ---
    # Rotating a token is a student's remedy for a leak, so keep this short.
    identity_cache_ttl_seconds: float = 45
    identity_negative_cache_ttl_seconds: float = 3
    roster_cache_ttl_seconds: float = 60
    platform_timeout_seconds: float = 5
    rate_limit_per_second: float = 60
    rate_limit_burst: int = 60

    # --- board defaults, until an admin changes them ---
    default_accept_threshold: int = 5
    default_reject_threshold: int = 5

    log_level: str = "INFO"

    @property
    def docs_base_url(self) -> str:
        """Where the API lives, for copy-pasteable examples in the docs."""
        return (self.public_base_url or "http://localhost:8000").rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
