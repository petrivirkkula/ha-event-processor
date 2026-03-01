"""Tests for custom exceptions."""
import pytest
from ha_event_processor.exceptions import (
    HAEventProcessorException,
    MQTTConnectionError,
    MQTTSubscriptionError,
    StorageError,
    EventValidationError,
    GCPSyncError,
    ConfigurationError,
)


class TestExceptions:
    """Test custom exception hierarchy."""

    def test_base_exception(self):
        """Test base exception."""
        exc = HAEventProcessorException("Test error")
        assert str(exc) == "Test error"
        assert isinstance(exc, Exception)

    def test_mqtt_connection_error(self):
        """Test MQTT connection error."""
        exc = MQTTConnectionError("Connection failed")
        assert str(exc) == "Connection failed"
        assert isinstance(exc, HAEventProcessorException)

    def test_mqtt_subscription_error(self):
        """Test MQTT subscription error."""
        exc = MQTTSubscriptionError("Subscription failed")
        assert str(exc) == "Subscription failed"
        assert isinstance(exc, HAEventProcessorException)

    def test_storage_error(self):
        """Test storage error."""
        exc = StorageError("Database error")
        assert str(exc) == "Database error"
        assert isinstance(exc, HAEventProcessorException)

    def test_event_validation_error(self):
        """Test event validation error."""
        exc = EventValidationError("Invalid event")
        assert str(exc) == "Invalid event"
        assert isinstance(exc, HAEventProcessorException)

    def test_gcp_sync_error(self):
        """Test GCP sync error."""
        exc = GCPSyncError("Sync failed")
        assert str(exc) == "Sync failed"
        assert isinstance(exc, HAEventProcessorException)

    def test_configuration_error(self):
        """Test configuration error."""
        exc = ConfigurationError("Invalid config")
        assert str(exc) == "Invalid config"
        assert isinstance(exc, HAEventProcessorException)

    def test_exception_hierarchy(self):
        """Test exception hierarchy."""
        errors = [
            MQTTConnectionError("test"),
            MQTTSubscriptionError("test"),
            StorageError("test"),
            EventValidationError("test"),
            GCPSyncError("test"),
            ConfigurationError("test"),
        ]

        for error in errors:
            assert isinstance(error, HAEventProcessorException)
            assert isinstance(error, Exception)

    def test_exception_can_be_raised(self):
        """Test that exceptions can be raised and caught."""
        with pytest.raises(HAEventProcessorException):
            raise MQTTConnectionError("Test")

        with pytest.raises(EventValidationError):
            raise EventValidationError("Test")

        with pytest.raises(StorageError):
            raise StorageError("Test")

    def test_exception_message_preserved(self):
        """Test that exception message is preserved."""
        message = "Custom error message"
        exc = HAEventProcessorException(message)
        assert str(exc) == message

