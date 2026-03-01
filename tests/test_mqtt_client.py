"""Tests for MQTT client module."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, call
from ha_event_processor.mqtt.client import MQTTClient
from ha_event_processor.exceptions import MQTTConnectionError


class TestMQTTClient:
    """Test MQTTClient class."""

    @pytest.fixture
    def callback(self):
        """Create a mock callback function."""
        return Mock()

    @pytest.fixture
    def mqtt_client(self, callback):
        """Create an MQTT client with mock."""
        with patch('ha_event_processor.mqtt.client.mqtt.Client'):
            client = MQTTClient(callback)
            return client

    def test_initialization(self, callback):
        """Test MQTT client initialization."""
        with patch('ha_event_processor.mqtt.client.mqtt.Client'):
            client = MQTTClient(callback)
            assert client.on_message_callback == callback
            assert client.is_connected is False

    def test_connect_success(self, mqtt_client):
        """Test successful connection."""
        mqtt_client.client.connect = Mock()
        mqtt_client.client.loop_start = Mock()

        mqtt_client.connect()

        mqtt_client.client.connect.assert_called_once()
        mqtt_client.client.loop_start.assert_called_once()

    def test_connect_with_credentials(self, callback):
        """Test connection with MQTT credentials."""
        with patch('ha_event_processor.mqtt.client.mqtt.Client') as mock_mqtt:
            with patch.dict('os.environ', {
                'MQTT_USERNAME': 'user',
                'MQTT_PASSWORD': 'pass'
            }):
                with patch('ha_event_processor.mqtt.client.settings') as mock_settings:
                    mock_settings.mqtt_username = 'user'
                    mock_settings.mqtt_password = 'pass'
                    mock_settings.mqtt_broker_host = 'localhost'
                    mock_settings.mqtt_broker_port = 1883
                    mock_settings.mqtt_client_id = 'test'
                    # Ensure numeric defaults
                    mock_settings.max_retries = 3
                    mock_settings.event_retention_days = 30

                    client = MQTTClient(callback)
                    client.client.username_pw_set = Mock()
                    client.client.connect = Mock()
                    client.client.loop_start = Mock()

                    client.connect()

                    client.client.username_pw_set.assert_called_once()

    def test_subscribe(self, mqtt_client):
        """Test topic subscription."""
        mqtt_client.client.subscribe = Mock()

        mqtt_client.subscribe("homeassistant/#")

        mqtt_client.client.subscribe.assert_called_once_with("homeassistant/#", qos=1)

    def test_subscribe_default_topic(self, mqtt_client):
        """Test subscription with default topic."""
        mqtt_client.client.subscribe = Mock()

        with patch('ha_event_processor.mqtt.client.settings') as mock_settings:
            mock_settings.mqtt_topic_prefix = "homeassistant/"
            mqtt_client.subscribe()

            mqtt_client.client.subscribe.assert_called_once()

    def test_disconnect(self, mqtt_client):
        """Test disconnection."""
        mqtt_client.client.loop_stop = Mock()
        mqtt_client.client.disconnect = Mock()
        mqtt_client.is_connected = True

        mqtt_client.disconnect()

        mqtt_client.client.loop_stop.assert_called_once()
        mqtt_client.client.disconnect.assert_called_once()
        assert mqtt_client.is_connected is False

    def test_on_connect_success(self, mqtt_client):
        """Test on_connect callback on success."""
        mqtt_client.subscribe = Mock()
        mqtt_client._on_connect(mqtt_client.client, None, {}, 0)

        assert mqtt_client.is_connected is True
        mqtt_client.subscribe.assert_called_once()

    def test_on_connect_failure(self, mqtt_client):
        """Test on_connect callback on failure."""
        mqtt_client._on_connect(mqtt_client.client, None, {}, 1)

        assert mqtt_client.is_connected is False

    def test_on_disconnect(self, mqtt_client):
        """Test on_disconnect callback."""
        mqtt_client.is_connected = True
        mqtt_client._on_disconnect(mqtt_client.client, None, 0)

        assert mqtt_client.is_connected is False

    def test_parse_valid_event(self, mqtt_client):
        """Test parsing valid MQTT event."""
        topic = "homeassistant/light/living_room/state"
        payload = '{"state": "on", "brightness": 255}'

        with patch('ha_event_processor.mqtt.client.settings') as mock_settings:
            mock_settings.mqtt_topic_prefix = "homeassistant/"
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            event = mqtt_client._parse_event(topic, payload)

            assert event is not None
            assert event["entity_id"] == "light.living_room"
            assert event["domain"] == "light"
            assert event["event_type"] == "state_changed"

    def test_parse_simple_payload(self, mqtt_client):
        """Test parsing simple string payload."""
        topic = "homeassistant/sensor/temperature/state"
        payload = "22.5"

        with patch('ha_event_processor.mqtt.client.settings') as mock_settings:
            mock_settings.mqtt_topic_prefix = "homeassistant/"
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            event = mqtt_client._parse_event(topic, payload)

            assert event is not None
            assert event["state"] == "22.5"
            assert event["entity_id"] == "sensor.temperature"

    def test_parse_invalid_topic_prefix(self, mqtt_client):
        """Test parsing with invalid topic prefix."""
        topic = "other/light/living_room/state"
        payload = '{"state": "on"}'

        with patch('ha_event_processor.mqtt.client.settings') as mock_settings:
            mock_settings.mqtt_topic_prefix = "homeassistant/"
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            event = mqtt_client._parse_event(topic, payload)

            assert event is None

    def test_parse_malformed_json_payload(self, mqtt_client):
        """Test parsing malformed JSON payload."""
        topic = "homeassistant/light/living_room/state"
        payload = "invalid json {"

        with patch('ha_event_processor.mqtt.client.settings') as mock_settings:
            mock_settings.mqtt_topic_prefix = "homeassistant/"
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            event = mqtt_client._parse_event(topic, payload)

            assert event is not None
            assert event["state"] == "invalid json {"

    def test_on_message_valid_event(self, mqtt_client, callback):
        """Test on_message with valid event."""
        message = Mock()
        message.topic = "homeassistant/light/living_room/state"
        message.payload = b'{"state": "on"}'

        with patch('ha_event_processor.mqtt.client.settings') as mock_settings:
            mock_settings.mqtt_topic_prefix = "homeassistant/"
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            mqtt_client._on_message(mqtt_client.client, None, message)

            callback.assert_called_once()

    def test_on_message_invalid_event(self, mqtt_client, callback):
        """Test on_message with invalid event."""
        message = Mock()
        message.topic = "other/topic"
        message.payload = b'{"state": "on"}'

        with patch('ha_event_processor.mqtt.client.settings') as mock_settings:
            mock_settings.mqtt_topic_prefix = "homeassistant/"
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            mqtt_client._on_message(mqtt_client.client, None, message)

            callback.assert_not_called()

    def test_on_message_error_handling(self, mqtt_client, callback):
        """Test on_message error handling."""
        message = Mock()
        message.topic = None  # Will cause error
        message.payload = b'{"state": "on"}'

        # Should not raise exception
        mqtt_client._on_message(mqtt_client.client, None, message)

        # Error should be logged but not raised
        assert True

    def test_multiple_event_parsing(self, mqtt_client):
        """Test parsing multiple different events."""
        events = [
            ("homeassistant/light/room1/state", '{"state": "on"}'),
            ("homeassistant/switch/pump/state", '{"state": "off"}'),
            ("homeassistant/sensor/temp/state", "25.3"),
            ("homeassistant/binary_sensor/motion/state", "on"),
        ]

        with patch('ha_event_processor.mqtt.client.settings') as mock_settings:
            mock_settings.mqtt_topic_prefix = "homeassistant/"
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            for topic, payload in events:
                event = mqtt_client._parse_event(topic, payload)
                assert event is not None
                assert "entity_id" in event
                assert "domain" in event

