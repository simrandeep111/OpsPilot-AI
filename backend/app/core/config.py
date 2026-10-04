import os
from dataclasses import dataclass


def _enabled(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    monitoring_enabled: bool = _enabled("MONITORING_ENABLED")
    monitoring_interval_seconds: int = int(os.getenv("MONITORING_INTERVAL_SECONDS", "60"))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    )
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    jev_model: str = os.getenv("JEV_MODEL", "typesafe/jev-1.13")
    jev_incident_probability: float = float(os.getenv("JEV_INCIDENT_PROBABILITY", "0.70"))
    ai_provider: str | None = os.getenv("AI_PROVIDER") or ("groq" if os.getenv("GROQ_API_KEY") else None)
    ai_api_key: str | None = os.getenv("AI_API_KEY") or os.getenv("GROQ_API_KEY")
    ai_model: str | None = (
        os.getenv("AI_MODEL")
        or os.getenv("GROQ_MODEL")
        or ("openai/gpt-oss-20b" if os.getenv("GROQ_API_KEY") else None)
    )
    slack_webhook_url: str | None = os.getenv("SLACK_WEBHOOK_URL")
    prometheus_url: str | None = os.getenv("PROMETHEUS_URL")
    prometheus_auth_type: str = os.getenv("PROMETHEUS_AUTH_TYPE", "none")
    prometheus_username: str | None = os.getenv("PROMETHEUS_USERNAME")
    prometheus_password: str | None = os.getenv("PROMETHEUS_PASSWORD")
    prometheus_token: str | None = os.getenv("PROMETHEUS_TOKEN")
    prometheus_service_name: str = os.getenv("PROMETHEUS_SERVICE_NAME", "prometheus")
    prometheus_allow_private: bool = _enabled("PROMETHEUS_ALLOW_PRIVATE")


settings = Settings()
