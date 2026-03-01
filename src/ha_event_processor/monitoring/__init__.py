"""Prometheus metrics for monitoring."""
from prometheus_client import Counter, Gauge, Histogram
import time

# Counters
events_received_total = Counter(
    "ha_events_received_total",
    "Total number of events received from MQTT",
    ["domain"],
)

events_stored_total = Counter(
    "ha_events_stored_total",
    "Total number of events stored in database",
    ["domain"],
)

events_synced_total = Counter(
    "ha_events_synced_total",
    "Total number of events synced to GCP",
    ["status"],
)

sync_errors_total = Counter(
    "ha_sync_errors_total",
    "Total number of sync errors",
    ["error_type"],
)

# Gauges
events_pending = Gauge(
    "ha_events_pending_total",
    "Number of events pending GCP sync",
)

mqtt_connected = Gauge(
    "ha_mqtt_connected",
    "MQTT connection status (1=connected, 0=disconnected)",
)

gcp_connected = Gauge(
    "ha_gcp_connected",
    "GCP connection status (1=connected, 0=disconnected)",
)

# Histograms
event_processing_time = Histogram(
    "ha_event_processing_duration_seconds",
    "Event processing duration in seconds",
)

gcp_sync_duration = Histogram(
    "ha_gcp_sync_duration_seconds",
    "GCP sync duration in seconds",
)


def record_event_received(domain: str = "unknown"):
    """Record an event received."""
    events_received_total.labels(domain=domain).inc()


def record_event_stored(domain: str = "unknown"):
    """Record an event stored."""
    events_stored_total.labels(domain=domain).inc()


def record_event_synced(status: str = "success"):
    """Record an event synced."""
    events_synced_total.labels(status=status).inc()


def record_sync_error(error_type: str = "unknown"):
    """Record a sync error."""
    sync_errors_total.labels(error_type=error_type).inc()


def set_pending_events(count: int):
    """Set the number of pending events."""
    events_pending.set(count)


def set_mqtt_connected(connected: bool):
    """Set MQTT connection status."""
    mqtt_connected.set(1 if connected else 0)


def set_gcp_connected(connected: bool):
    """Set GCP connection status."""
    gcp_connected.set(1 if connected else 0)

