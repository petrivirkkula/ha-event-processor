"""Test configuration and fixtures."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    yield f"sqlite:///{db_path}"
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    os.rmdir(temp_dir)


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client."""
    with patch('paho.mqtt.client.Client') as mock:
        yield mock


@pytest.fixture
def mock_bigquery_client():
    """Create a mock BigQuery client."""
    with patch('google.cloud.bigquery.Client') as mock:
        yield mock


@pytest.fixture
def sample_event():
    """Sample event data for testing."""
    return {
        "entity_id": "light.living_room",
        "event_type": "state_changed",
        "domain": "light",
        "state": "on",
        "attributes": '{"brightness": 255}',
        "timestamp": None,
        "service": None,
        "raw_payload": '{"state": "on", "brightness": 255}'
    }


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.mqtt_broker_host = "localhost"
    settings.mqtt_broker_port = 1883
    settings.mqtt_username = None
    settings.mqtt_password = None
    settings.mqtt_client_id = "test-client"
    settings.mqtt_reconnect_delay = 5
    settings.database_url = "sqlite:///:memory:"
    settings.gcp_project_id = "test-project"
    settings.enable_gcp_sync = False
    settings.max_retries = 3
    settings.event_retention_days = 30
    settings.database_pool_size = 5
    return settings


# Autouse fixture to ensure real settings have sane defaults during tests
@pytest.fixture(autouse=True)
def _apply_global_settings_defaults(monkeypatch):
    """Apply safe defaults to the real settings object used by modules.

    This avoids cases where tests patch module-specific `settings` or rely on
    attributes which would otherwise be MagicMock and could be passed into
    SQLAlchemy/SQLite bindings causing ProgrammingError.
    """
    try:
        from ha_event_processor.config import settings as real_settings
    except Exception:
        real_settings = None

    if real_settings is not None:
        # Numeric defaults
        monkeypatch.setattr(real_settings, "max_retries", 3, raising=False)
        monkeypatch.setattr(real_settings, "event_retention_days", 30, raising=False)
        monkeypatch.setattr(real_settings, "database_pool_size", 5, raising=False)
        # MQTT defaults
        monkeypatch.setattr(real_settings, "mqtt_broker_host", "localhost", raising=False)
        monkeypatch.setattr(real_settings, "mqtt_broker_port", 1883, raising=False)
        monkeypatch.setattr(real_settings, "mqtt_topic_prefix", "homeassistant/", raising=False)
        # GCP defaults
        monkeypatch.setattr(real_settings, "gcp_batch_size", 100, raising=False)
        monkeypatch.setattr(real_settings, "gcp_batch_timeout_seconds", 300, raising=False)

    yield

