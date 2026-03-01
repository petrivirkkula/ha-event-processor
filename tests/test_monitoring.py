"""Tests for monitoring and metrics module."""
import pytest
from unittest.mock import patch, Mock
from ha_event_processor.monitoring import (
    record_event_received,
    record_event_stored,
    record_event_synced,
    record_sync_error,
    set_pending_events,
    set_mqtt_connected,
    set_gcp_connected,
    events_received_total,
    events_stored_total,
    events_synced_total,
    sync_errors_total,
    events_pending,
    mqtt_connected,
    gcp_connected,
)


class TestMetrics:
    """Test metrics recording functions."""

    def test_record_event_received(self):
        """Test recording received event."""
        with patch.object(events_received_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            record_event_received("light")

            mock_labels.assert_called_with(domain="light")
            mock_counter.inc.assert_called_once()

    def test_record_event_received_default_domain(self):
        """Test recording received event with default domain."""
        with patch.object(events_received_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            record_event_received()

            mock_labels.assert_called_with(domain="unknown")
            mock_counter.inc.assert_called_once()

    def test_record_event_stored(self):
        """Test recording stored event."""
        with patch.object(events_stored_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            record_event_stored("sensor")

            mock_labels.assert_called_with(domain="sensor")
            mock_counter.inc.assert_called_once()

    def test_record_event_synced(self):
        """Test recording synced event."""
        with patch.object(events_synced_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            record_event_synced("success")

            mock_labels.assert_called_with(status="success")
            mock_counter.inc.assert_called_once()

    def test_record_event_synced_failure(self):
        """Test recording failed sync."""
        with patch.object(events_synced_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            record_event_synced("failure")

            mock_labels.assert_called_with(status="failure")
            mock_counter.inc.assert_called_once()

    def test_record_sync_error(self):
        """Test recording sync error."""
        with patch.object(sync_errors_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            record_sync_error("timeout")

            mock_labels.assert_called_with(error_type="timeout")
            mock_counter.inc.assert_called_once()

    def test_record_sync_error_default(self):
        """Test recording sync error with default type."""
        with patch.object(sync_errors_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            record_sync_error()

            mock_labels.assert_called_with(error_type="unknown")
            mock_counter.inc.assert_called_once()

    def test_set_pending_events(self):
        """Test setting pending events gauge."""
        with patch.object(events_pending, 'set') as mock_set:
            set_pending_events(42)

            mock_set.assert_called_once_with(42)

    def test_set_pending_events_zero(self):
        """Test setting pending events to zero."""
        with patch.object(events_pending, 'set') as mock_set:
            set_pending_events(0)

            mock_set.assert_called_once_with(0)

    def test_set_mqtt_connected_true(self):
        """Test setting MQTT connected status to true."""
        with patch.object(mqtt_connected, 'set') as mock_set:
            set_mqtt_connected(True)

            mock_set.assert_called_once_with(1)

    def test_set_mqtt_connected_false(self):
        """Test setting MQTT connected status to false."""
        with patch.object(mqtt_connected, 'set') as mock_set:
            set_mqtt_connected(False)

            mock_set.assert_called_once_with(0)

    def test_set_gcp_connected_true(self):
        """Test setting GCP connected status to true."""
        with patch.object(gcp_connected, 'set') as mock_set:
            set_gcp_connected(True)

            mock_set.assert_called_once_with(1)

    def test_set_gcp_connected_false(self):
        """Test setting GCP connected status to false."""
        with patch.object(gcp_connected, 'set') as mock_set:
            set_gcp_connected(False)

            mock_set.assert_called_once_with(0)

    def test_multiple_domains_recording(self):
        """Test recording events from multiple domains."""
        with patch.object(events_received_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            domains = ["light", "switch", "sensor", "binary_sensor"]
            for domain in domains:
                record_event_received(domain)

            assert mock_labels.call_count == 4

    def test_metric_counters_incremented(self):
        """Test that counters are incremented correctly."""
        with patch.object(events_received_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            for _ in range(5):
                record_event_received("light")

            assert mock_counter.inc.call_count == 5

    def test_pending_events_gauge_values(self):
        """Test setting various pending event counts."""
        with patch.object(events_pending, 'set') as mock_set:
            values = [0, 1, 10, 100, 1000, 999999]
            for value in values:
                set_pending_events(value)

            assert mock_set.call_count == len(values)

    def test_sync_status_recording(self):
        """Test recording different sync statuses."""
        statuses = ["success", "failure", "partial"]

        with patch.object(events_synced_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            for status in statuses:
                record_event_synced(status)

            assert mock_labels.call_count == len(statuses)

    def test_connection_status_transitions(self):
        """Test recording connection status transitions."""
        with patch.object(mqtt_connected, 'set') as mock_mqtt_set:
            # Simulate connection sequence
            set_mqtt_connected(False)  # Disconnected
            set_mqtt_connected(True)   # Connected
            set_mqtt_connected(False)  # Disconnected
            set_mqtt_connected(True)   # Connected

            calls = [
                mock_mqtt_set.call_args_list[i][0][0]
                for i in range(len(mock_mqtt_set.call_args_list))
            ]
            assert calls == [0, 1, 0, 1]

    def test_error_types_recording(self):
        """Test recording various error types."""
        error_types = [
            "timeout",
            "authentication",
            "invalid_json",
            "network",
            "database",
            "api_error"
        ]

        with patch.object(sync_errors_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            for error_type in error_types:
                record_sync_error(error_type)

            assert mock_labels.call_count == len(error_types)

