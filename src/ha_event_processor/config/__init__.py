"""Configuration management for HA Event Processor."""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MQTT Configuration
    mqtt_broker_host: str = os.getenv("MQTT_BROKER_HOST", "localhost")
    mqtt_broker_port: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    mqtt_username: Optional[str] = os.getenv("MQTT_USERNAME")
    mqtt_password: Optional[str] = os.getenv("MQTT_PASSWORD")
    mqtt_topic_prefix: str = os.getenv("MQTT_TOPIC_PREFIX", "homeassistant/")
    mqtt_client_id: str = os.getenv("MQTT_CLIENT_ID", "ha_event_processor")
    mqtt_reconnect_delay: int = int(os.getenv("MQTT_RECONNECT_DELAY", "5"))

    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./ha_events.db")
    database_pool_size: int = int(os.getenv("DATABASE_POOL_SIZE", "5"))

    # Google Cloud Configuration
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "")
    gcp_dataset_id: str = os.getenv("GCP_DATASET_ID", "ha_events")
    gcp_table_id: str = os.getenv("GCP_TABLE_ID", "events")
    gcp_service_account_json: Optional[str] = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    gcp_batch_size: int = int(os.getenv("GCP_BATCH_SIZE", "100"))
    gcp_batch_timeout_seconds: int = int(os.getenv("GCP_BATCH_TIMEOUT_SECONDS", "300"))

    # Processing Configuration
    enable_gcp_sync: bool = os.getenv("ENABLE_GCP_SYNC", "true").lower() == "true"
    event_retention_days: int = int(os.getenv("EVENT_RETENTION_DAYS", "30"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_backoff_factor: float = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))

    # Server Configuration
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    verbose_logging: bool = os.getenv("VERBOSE_LOGGING", False)

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

