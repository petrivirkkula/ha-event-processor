"""Tests for storage module."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from ha_event_processor.storage.database import Database
from ha_event_processor.storage.models import Event
from ha_event_processor.exceptions import StorageError


class TestDatabase:
    """Test Database class."""

    @pytest.fixture
    def in_memory_db(self):
        """Create in-memory SQLite database for testing."""
        with patch('ha_event_processor.storage.database.settings') as mock_settings:
            mock_settings.database_url = "sqlite:///:memory:"
            mock_settings.database_pool_size = 5
            # Ensure numeric settings are present to avoid MagicMock being used in queries
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            db = Database()
            yield db
            db.close()

    def test_database_initialization(self, in_memory_db):
        """Test database initialization."""
        assert in_memory_db.engine is not None
        assert in_memory_db.SessionLocal is not None

    def test_add_event(self, in_memory_db):
        """Test adding an event."""
        event = in_memory_db.add_event(
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on"
        )

        assert event.id is not None
        assert event.entity_id == "light.test"
        assert event.domain == "light"
        assert event.state == "on"
        assert event.synced_to_gcp is False

    def test_add_event_with_attributes(self, in_memory_db):
        """Test adding event with attributes."""
        attributes = '{"brightness": 255, "color_temp": 3000}'
        event = in_memory_db.add_event(
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on",
            attributes=attributes
        )

        assert event.attributes == attributes

    def test_add_event_with_timestamp(self, in_memory_db):
        """Test adding event with custom timestamp."""
        now = datetime.utcnow()
        event = in_memory_db.add_event(
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on",
            timestamp=now
        )

        assert event.timestamp == now

    def test_add_event_with_raw_payload(self, in_memory_db):
        """Test adding event with raw payload."""
        payload = '{"action": "turn_on", "source": "automation"}'
        event = in_memory_db.add_event(
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on",
            raw_payload=payload
        )

        assert event.raw_payload == payload

    def test_get_unsynced_events(self, in_memory_db):
        """Test retrieving unsynced events."""
        # Add multiple events
        for i in range(5):
            in_memory_db.add_event(
                entity_id=f"light.test{i}",
                event_type="state_changed",
                domain="light",
                state="on"
            )

        unsynced = in_memory_db.get_unsynced_events()

        assert len(unsynced) == 5
        assert all(not e.synced_to_gcp for e in unsynced)

    def test_get_unsynced_events_with_limit(self, in_memory_db):
        """Test retrieving unsynced events with limit."""
        # Add 10 events
        for i in range(10):
            in_memory_db.add_event(
                entity_id=f"light.test{i}",
                event_type="state_changed",
                domain="light",
                state="on"
            )

        unsynced = in_memory_db.get_unsynced_events(limit=3)

        assert len(unsynced) == 3

    def test_mark_synced(self, in_memory_db):
        """Test marking events as synced."""
        events = []
        for i in range(3):
            event = in_memory_db.add_event(
                entity_id=f"light.test{i}",
                event_type="state_changed",
                domain="light",
                state="on"
            )
            events.append(event)

        event_ids = [e.id for e in events]
        in_memory_db.mark_synced(event_ids)

        # Verify all are marked as synced
        unsynced = in_memory_db.get_unsynced_events()
        assert len(unsynced) == 0

    def test_mark_sync_failed(self, in_memory_db):
        """Test marking event as sync failed."""
        event = in_memory_db.add_event(
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on"
        )

        in_memory_db.mark_sync_failed(event.id, "Connection timeout")

        session = in_memory_db.get_session()
        updated_event = session.query(Event).filter(Event.id == event.id).first()
        session.close()

        assert updated_event.retry_count == 1
        assert "Connection timeout" in updated_event.sync_error

    def test_cleanup_old_events(self, in_memory_db):
        """Test cleanup of old events."""
        # Add old event (30 days old)
        old_time = datetime.utcnow() - timedelta(days=31)
        old_event = in_memory_db.add_event(
            entity_id="light.old",
            event_type="state_changed",
            domain="light",
            state="on",
            timestamp=old_time
        )

        # Add new event
        new_event = in_memory_db.add_event(
            entity_id="light.new",
            event_type="state_changed",
            domain="light",
            state="on"
        )

        # Cleanup events older than 30 days
        deleted = in_memory_db.cleanup_old_events(days=30)

        assert deleted == 1

        # Verify old event is deleted
        remaining = in_memory_db.get_event_count()
        assert remaining == 1

    def test_get_event_count(self, in_memory_db):
        """Test getting event count."""
        # Add 5 events
        for i in range(5):
            in_memory_db.add_event(
                entity_id=f"light.test{i}",
                event_type="state_changed",
                domain="light",
                state="on"
            )

        count = in_memory_db.get_event_count()
        assert count == 5

    def test_get_event_count_synced(self, in_memory_db):
        """Test getting count of synced events."""
        # Add 5 events
        for i in range(5):
            in_memory_db.add_event(
                entity_id=f"light.test{i}",
                event_type="state_changed",
                domain="light",
                state="on"
            )

        # Mark 2 as synced
        unsynced = in_memory_db.get_unsynced_events(limit=2)
        ids = [e.id for e in unsynced]
        in_memory_db.mark_synced(ids)

        synced_count = in_memory_db.get_event_count(synced=True)
        unsynced_count = in_memory_db.get_event_count(synced=False)

        assert synced_count == 2
        assert unsynced_count == 3

    def test_event_timestamps_are_set(self, in_memory_db):
        """Test that event timestamps are automatically set."""
        event = in_memory_db.add_event(
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on"
        )

        assert event.created_at is not None
        assert event.updated_at is not None
        assert isinstance(event.created_at, datetime)

    def test_database_session_management(self, in_memory_db):
        """Test proper session management."""
        session = in_memory_db.get_session()
        assert session is not None
        session.close()

    def test_add_event_database_error(self, in_memory_db):
        """Test error handling when adding event."""
        in_memory_db.add_event(
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on"
        )

        # This should not raise, but return None or handle gracefully
        event = in_memory_db.add_event(
            entity_id="light.test",
            event_type="state_changed",
            domain="light"
        )

        assert event is not None

    def test_event_retry_count_tracking(self, in_memory_db):
        """Test retry count is tracked for sync failures."""
        event = in_memory_db.add_event(
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on"
        )

        # Simulate multiple failed sync attempts
        for i in range(3):
            in_memory_db.mark_sync_failed(event.id, f"Attempt {i+1} failed")

        session = in_memory_db.get_session()
        updated = session.query(Event).filter(Event.id == event.id).first()
        session.close()

        assert updated.retry_count == 3

    def test_close_database(self, in_memory_db):
        """Test closing database connection."""
        in_memory_db.close()
        # Should not raise exception
        assert True

