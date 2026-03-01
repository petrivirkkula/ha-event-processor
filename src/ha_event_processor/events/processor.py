"""Event processing and routing."""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..config import settings
from ..exceptions import EventValidationError
from ..storage.database import Database

logger = logging.getLogger(__name__)


class EventProcessor:
    """Process and validate Home Assistant events."""

    def __init__(self, database: Database):
        """Initialize event processor.

        Args:
            database: Database instance for storing events
        """
        self.database = database

    def process_event(self, event_data: Dict[str, Any]) -> Optional[int]:
        """Process and store an event.

        Args:
            event_data: Raw event data from MQTT

        Returns:
            Event ID if successful, None otherwise
        """
        try:
            # Validate event
            validated_event = self._validate_event(event_data)

            # Store in database
            event = self.database.add_event(
                entity_id=validated_event["entity_id"],
                event_type=validated_event["event_type"],
                domain=validated_event["domain"],
                state=validated_event.get("state"),
                attributes=validated_event.get("attributes"),
                timestamp=validated_event.get("timestamp"),
                service=validated_event.get("service"),
                raw_payload=validated_event.get("raw_payload"),
            )

            logger.info(f"Event processed: {event.id} ({event.entity_id})")
            return event.id

        except EventValidationError as e:
            logger.warning(f"Event validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            return None

    def _validate_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate event data.

        Args:
            event_data: Raw event data

        Returns:
            Validated event data

        Raises:
            EventValidationError: If event is invalid
        """
        # Check required fields
        required_fields = ["entity_id", "event_type", "domain"]
        for field in required_fields:
            if field not in event_data or not event_data[field]:
                raise EventValidationError(f"Missing required field: {field}")

        # Normalize entity_id
        entity_id = event_data["entity_id"].lower()
        if not self._is_valid_entity_id(entity_id):
            raise EventValidationError(f"Invalid entity_id: {entity_id}")

        # Normalize state
        state = event_data.get("state")
        if state:
            state = str(state).strip()

        # Normalize attributes
        attributes = event_data.get("attributes")
        if attributes and isinstance(attributes, str):
            try:
                json.loads(attributes)  # Validate JSON
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in attributes, storing as string")

        return {
            "entity_id": entity_id,
            "event_type": event_data.get("event_type", "state_changed"),
            "domain": event_data.get("domain", "").lower(),
            "state": state,
            "attributes": attributes,
            "timestamp": event_data.get("timestamp") or datetime.utcnow(),
            "service": event_data.get("service"),
            "raw_payload": event_data.get("raw_payload"),
        }

    def _is_valid_entity_id(self, entity_id: str) -> bool:
        """Validate entity_id format.

        Format: domain.entity_name
        """
        if not isinstance(entity_id, str):
            return False

        parts = entity_id.split(".")
        if len(parts) != 2:
            return False

        domain, name = parts
        return bool(domain.isidentifier() or "_" in domain) and bool(
            name.isidentifier() or "_" in name
        )

