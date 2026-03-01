"""Tests for configuration module."""
import pytest
import os
from unittest.mock import patch
from ha_event_processor.config import Settings, settings


class TestSettings:
    """Test Settings class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        s = Settings()
        assert s.mqtt_broker_host == "localhost"
        assert s.mqtt_broker_port == 1883
        assert s.server_host == "0.0.0.0"
        assert s.server_port == 8000
        assert s.log_level == "INFO"

    def test_mqtt_configuration(self):
        """Test MQTT configuration loading."""
        with patch.dict(os.environ, {
            "MQTT_BROKER_HOST": "mqtt.example.com",
            "MQTT_BROKER_PORT": "8883",
            "MQTT_CLIENT_ID": "custom-client"
        }):
            s = Settings()
            assert s.mqtt_broker_host == "mqtt.example.com"
            assert s.mqtt_broker_port == 8883
            assert s.mqtt_client_id == "custom-client"

    def test_database_url(self):
        """Test database URL configuration."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@host:5432/db"
        }):
            s = Settings()
            assert s.database_url == "postgresql://user:pass@host:5432/db"

    def test_gcp_configuration(self):
        """Test GCP configuration."""
        with patch.dict(os.environ, {
            "GCP_PROJECT_ID": "my-project",
            "GCP_DATASET_ID": "custom_dataset",
            "ENABLE_GCP_SYNC": "false"
        }):
            s = Settings()
            assert s.gcp_project_id == "my-project"
            assert s.gcp_dataset_id == "custom_dataset"
            assert s.enable_gcp_sync is False

    def test_enable_gcp_sync_parsing(self):
        """Test GCP sync enabled parsing."""
        with patch.dict(os.environ, {"ENABLE_GCP_SYNC": "true"}):
            s = Settings()
            assert s.enable_gcp_sync is True

        with patch.dict(os.environ, {"ENABLE_GCP_SYNC": "false"}):
            s = Settings()
            assert s.enable_gcp_sync is False

    def test_integer_parsing(self):
        """Test integer configuration parsing."""
        with patch.dict(os.environ, {
            "MQTT_BROKER_PORT": "9999",
            "SERVER_PORT": "5000",
            "EVENT_RETENTION_DAYS": "60"
        }):
            s = Settings()
            assert s.mqtt_broker_port == 9999
            assert s.server_port == 5000
            assert s.event_retention_days == 60
            assert isinstance(s.mqtt_broker_port, int)

    def test_optional_mqtt_credentials(self):
        """Test optional MQTT credentials."""
        with patch.dict(os.environ, {
            "MQTT_USERNAME": "user",
            "MQTT_PASSWORD": "pass"
        }):
            s = Settings()
            assert s.mqtt_username == "user"
            assert s.mqtt_password == "pass"

    def test_batch_configuration(self):
        """Test batch processing configuration."""
        with patch.dict(os.environ, {
            "GCP_BATCH_SIZE": "500",
            "GCP_BATCH_TIMEOUT_SECONDS": "600"
        }):
            s = Settings()
            assert s.gcp_batch_size == 500
            assert s.gcp_batch_timeout_seconds == 600

    def test_retry_configuration(self):
        """Test retry configuration."""
        with patch.dict(os.environ, {
            "MAX_RETRIES": "5",
            "RETRY_BACKOFF_FACTOR": "3.0"
        }):
            s = Settings()
            assert s.max_retries == 5
            assert s.retry_backoff_factor == 3.0

    def test_log_level_configuration(self):
        """Test log level configuration."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                s = Settings()
                assert s.log_level == level

    def test_global_settings_instance(self):
        """Test that global settings instance is available."""
        assert settings is not None
        assert isinstance(settings, Settings)

