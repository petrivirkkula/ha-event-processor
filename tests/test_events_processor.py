"""Tests for event processor module."""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from ha_event_processor.events.processor import EventProcessor
from ha_event_processor.exceptions import EventValidationError


class TestEventProcessor:
    """Test EventProcessor class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return Mock()

    @pytest.fixture
    def processor(self, mock_db):
        """Create an event processor with mock database."""
        return EventProcessor(mock_db)

    def test_processor_initialization(self, mock_db):
        """Test processor initialization."""
        processor = EventProcessor(mock_db)
        assert processor.database == mock_db

    def test_valid_event_processing(self, processor, mock_db):
        """Test processing a valid event."""
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "domain": "light",
            "state": "on",
        }

        mock_db.add_event.return_value = Mock(id=1)

        result = processor.process_event(event_data)

        assert result == 1
        mock_db.add_event.assert_called_once()

    def test_missing_entity_id(self, processor):
        """Test event with missing entity_id."""
        event_data = {
            "event_type": "state_changed",
            "domain": "light",
            "state": "on",
        }

        result = processor.process_event(event_data)
        assert result is None

    def test_missing_event_type(self, processor):
        """Test event with missing event_type."""
        event_data = {
            "entity_id": "light.living_room",
            "domain": "light",
            "state": "on",
        }

        result = processor.process_event(event_data)
        assert result is None

    def test_missing_domain(self, processor):
        """Test event with missing domain."""
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "state": "on",
        }

        result = processor.process_event(event_data)
        assert result is None

    def test_invalid_entity_id_format(self, processor):
        """Test event with invalid entity_id format."""
        event_data = {
            "entity_id": "invalid_format",  # Missing dot
            "event_type": "state_changed",
            "domain": "light",
            "state": "on",
        }

        result = processor.process_event(event_data)
        assert result is None

    def test_entity_id_normalization(self, processor, mock_db):
        """Test entity_id is normalized to lowercase."""
        event_data = {
            "entity_id": "Light.Living_Room",
            "event_type": "state_changed",
            "domain": "light",
            "state": "on",
        }

        mock_db.add_event.return_value = Mock(id=1)
        processor.process_event(event_data)

        call_args = mock_db.add_event.call_args
        assert call_args[1]["entity_id"] == "light.living_room"

    def test_domain_normalization(self, processor, mock_db):
        """Test domain is normalized to lowercase."""
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "domain": "LIGHT",
            "state": "on",
        }

        mock_db.add_event.return_value = Mock(id=1)
        processor.process_event(event_data)

        call_args = mock_db.add_event.call_args
        assert call_args[1]["domain"] == "light"

    def test_state_normalization(self, processor, mock_db):
        """Test state is normalized."""
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "domain": "light",
            "state": "  ON  ",  # Extra spaces
        }

        mock_db.add_event.return_value = Mock(id=1)
        processor.process_event(event_data)

        call_args = mock_db.add_event.call_args
        assert call_args[1]["state"] == "ON"

    def test_attributes_json_validation(self, processor, mock_db):
        """Test attributes JSON validation."""
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "domain": "light",
            "state": "on",
            "attributes": '{"brightness": 255}',
        }

        mock_db.add_event.return_value = Mock(id=1)
        result = processor.process_event(event_data)

        assert result == 1

    def test_invalid_attributes_json(self, processor, mock_db):
        """Test invalid attributes JSON is stored as string."""
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "domain": "light",
            "state": "on",
            "attributes": "invalid json",
        }

        mock_db.add_event.return_value = Mock(id=1)
        result = processor.process_event(event_data)

        assert result == 1

    def test_timestamp_handling(self, processor, mock_db):
        """Test timestamp handling."""
        timestamp = datetime.utcnow()
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "domain": "light",
            "state": "on",
            "timestamp": timestamp,
        }

        mock_db.add_event.return_value = Mock(id=1)
        processor.process_event(event_data)

        call_args = mock_db.add_event.call_args
        assert call_args[1]["timestamp"] == timestamp

    def test_timestamp_default(self, processor, mock_db):
        """Test timestamp defaults to current time."""
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "domain": "light",
            "state": "on",
        }

        mock_db.add_event.return_value = Mock(id=1)
        processor.process_event(event_data)

        call_args = mock_db.add_event.call_args
        timestamp = call_args[1]["timestamp"]
        assert isinstance(timestamp, datetime)

    def test_database_error_handling(self, processor, mock_db):
        """Test database error handling."""
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "domain": "light",
            "state": "on",
        }

        mock_db.add_event.side_effect = Exception("Database error")
        result = processor.process_event(event_data)

        assert result is None

    def test_optional_fields(self, processor, mock_db):
        """Test processing with optional fields."""
        event_data = {
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "domain": "light",
            "service": "turn_on",
            "raw_payload": '{"action": "turn_on"}',
        }

        mock_db.add_event.return_value = Mock(id=1)
        result = processor.process_event(event_data)

        assert result == 1
        call_args = mock_db.add_event.call_args
        assert call_args[1]["service"] == "turn_on"
        assert call_args[1]["raw_payload"] == '{"action": "turn_on"}'

    def test_valid_entity_id_formats(self, processor):
        """Test various valid entity_id formats."""
        valid_ids = [
            "light.living_room",
            "sensor.temperature",
            "binary_sensor.motion",
            "switch.main_power",
            "light.room_1",
            "device_tracker.phone",
        ]

        for entity_id in valid_ids:
            assert processor._is_valid_entity_id(entity_id) is True

    def test_invalid_entity_id_formats(self, processor):
        """Test invalid entity_id formats."""
        invalid_ids = [
            "invalid",  # No dot
            ".invalid",  # Starts with dot
            "invalid.",  # Ends with dot
            "light..room",  # Double dot
            "light room",  # Space
            "",  # Empty
            123,  # Not string
        ]

        for entity_id in invalid_ids:
            assert processor._is_valid_entity_id(entity_id) is False

