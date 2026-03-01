"""MQTT client for receiving Home Assistant events."""
import json
import logging
import time
from typing import Callable, Optional
import paho.mqtt.client as mqtt

from ..config import settings
from ..exceptions import MQTTConnectionError, MQTTSubscriptionError, EventValidationError

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT client for subscribing to Home Assistant events."""

    def __init__(self, on_message_callback: Callable):
        """Initialize MQTT client.

        Args:
            on_message_callback: Callback function to handle received messages
        """
        self.on_message_callback = on_message_callback
        self.client = mqtt.Client(client_id=settings.mqtt_client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self.is_connected = False
        self._reconnect_delay = settings.mqtt_reconnect_delay

    def connect(self) -> None:
        """Connect to MQTT broker."""
        try:
            if settings.mqtt_username and settings.mqtt_password:
                self.client.username_pw_set(
                    settings.mqtt_username, settings.mqtt_password
                )

            logger.info(
                f"Connecting to MQTT broker: {settings.mqtt_broker_host}:"
                f"{settings.mqtt_broker_port}"
            )
            self.client.connect(
                settings.mqtt_broker_host, settings.mqtt_broker_port, keepalive=60
            )
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise MQTTConnectionError(f"Failed to connect to MQTT broker: {e}")

    def subscribe(self, topic: str = None) -> None:
        """Subscribe to MQTT topic.

        Args:
            topic: MQTT topic pattern (default: configured topic prefix)
        """
        try:
            topic = topic or f"{settings.mqtt_topic_prefix}#"
            logger.info(f"Subscribing to topic: {topic}")
            self.client.subscribe(topic, qos=1)
        except Exception as e:
            logger.error(f"Failed to subscribe to topic: {e}")
            raise MQTTSubscriptionError(f"Failed to subscribe to topic: {e}")

    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        logger.info("Disconnecting from MQTT broker")
        self.client.loop_stop()
        self.client.disconnect()
        self.is_connected = False

    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.is_connected = True
            self._reconnect_delay = settings.mqtt_reconnect_delay
            self.subscribe()
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
            self.is_connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection: {rc}")
            logger.info(f"Attempting to reconnect in {self._reconnect_delay} seconds")
            time.sleep(self._reconnect_delay)
            # Exponential backoff (max 5 minutes)
            self._reconnect_delay = min(self._reconnect_delay * 2, 300)
            try:
                self.connect()
            except MQTTConnectionError:
                logger.error("Reconnection failed")
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Handle subscription confirmation."""
        logger.info(f"Subscribed with QoS: {granted_qos}")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")

            logger.debug(f"Received message on {topic}: {payload[:100]}...")

            # Parse the event from topic and payload
            event_data = self._parse_event(topic, payload)
            if event_data:
                self.on_message_callback(event_data)
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _parse_event(self, topic: str, payload: str) -> Optional[dict]:
        """Parse Home Assistant event from MQTT topic and payload.

        Expected topic format: homeassistant/{domain}/{entity_id}/{component}
        Example: homeassistant/light/living_room/state
        """
        try:
            # Remove prefix and split topic
            if not topic.startswith(settings.mqtt_topic_prefix):
                return None

            topic_parts = topic[len(settings.mqtt_topic_prefix) :].split("/")

            # Try to parse as Home Assistant state topic
            if len(topic_parts) >= 3:
                domain = topic_parts[0]
                entity_id = topic_parts[1]
                component = topic_parts[2] if len(topic_parts) > 2 else None

                # Try to parse payload as JSON
                try:
                    attributes = json.loads(payload)
                    state = attributes.get("state")
                except (json.JSONDecodeError, AttributeError):
                    # Simple state value
                    attributes = None
                    state = payload

                return {
                    "entity_id": f"{domain}.{entity_id}",
                    "event_type": "state_changed",
                    "domain": domain,
                    "state": state,
                    "attributes": json.dumps(attributes) if attributes else None,
                    "raw_payload": payload,
                }
        except Exception as e:
            logger.warning(f"Failed to parse event from topic {topic}: {e}")

        return None

