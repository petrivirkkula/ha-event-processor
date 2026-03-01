"""Custom exceptions for HA Event Processor."""


class HAEventProcessorException(Exception):
    """Base exception for HA Event Processor."""

    pass


class MQTTConnectionError(HAEventProcessorException):
    """Raised when MQTT connection fails."""

    pass


class MQTTSubscriptionError(HAEventProcessorException):
    """Raised when MQTT subscription fails."""

    pass


class StorageError(HAEventProcessorException):
    """Raised when database operations fail."""

    pass


class EventValidationError(HAEventProcessorException):
    """Raised when event validation fails."""

    pass


class GCPSyncError(HAEventProcessorException):
    """Raised when Google Cloud sync fails."""

    pass


class ConfigurationError(HAEventProcessorException):
    """Raised when configuration is invalid."""

    pass

