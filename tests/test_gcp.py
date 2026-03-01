"""Tests for GCP BigQuery module."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from ha_event_processor.gcp import GCPUploader
from ha_event_processor.storage.models import Event
from ha_event_processor.exceptions import ConfigurationError, GCPSyncError


class TestGCPUploader:
    """Test GCPUploader class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return Mock()

    @pytest.fixture
    def mock_bigquery(self):
        """Create a mock BigQuery client."""
        with patch('ha_event_processor.gcp.bigquery.Client') as mock:
            yield mock

    @pytest.fixture
    def gcp_uploader(self, mock_db, mock_bigquery):
        """Create a GCP uploader with mocked clients."""
        with patch('ha_event_processor.gcp.settings') as mock_settings:
            mock_settings.gcp_project_id = "test-project"
            mock_settings.gcp_dataset_id = "test_dataset"
            mock_settings.gcp_table_id = "events"
            mock_settings.enable_gcp_sync = True
            mock_settings.gcp_service_account_json = None
            # Ensure numeric defaults
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            uploader = GCPUploader(mock_db)
            uploader.client = Mock()
            return uploader

    def test_uploader_initialization(self, mock_db):
        """Test uploader initialization."""
        with patch('ha_event_processor.gcp.settings') as mock_settings:
            mock_settings.gcp_project_id = "test-project"
            mock_settings.gcp_dataset_id = "test_dataset"
            mock_settings.gcp_table_id = "events"
            mock_settings.enable_gcp_sync = True
            mock_settings.gcp_service_account_json = None
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            with patch('ha_event_processor.gcp.bigquery.Client'):
                uploader = GCPUploader(mock_db)
                assert uploader.database == mock_db
                assert uploader.table_id == "test-project.test_dataset.events"

    def test_missing_project_id(self, mock_db):
        """Test error when GCP project ID is missing."""
        with patch('ha_event_processor.gcp.settings') as mock_settings:
            mock_settings.gcp_project_id = ""
            mock_settings.enable_gcp_sync = True
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            with pytest.raises(ConfigurationError):
                GCPUploader(mock_db)

    def test_upload_events_no_unsynced(self, gcp_uploader, mock_db):
        """Test upload when there are no unsynced events."""
        mock_db.get_unsynced_events.return_value = []

        count = gcp_uploader.upload_events()

        assert count == 0
        gcp_uploader.client.insert_rows_json.assert_not_called()

    def test_upload_events_success(self, gcp_uploader, mock_db):
        """Test successful event upload."""
        # Create mock events
        events = [
            Mock(
                id=1,
                timestamp=datetime.utcnow(),
                entity_id="light.test1",
                event_type="state_changed",
                domain="light",
                state="on",
                attributes='{"brightness": 255}',
                source="mqtt",
                synced_to_gcp=False
            ),
            Mock(
                id=2,
                timestamp=datetime.utcnow(),
                entity_id="light.test2",
                event_type="state_changed",
                domain="light",
                state="off",
                attributes=None,
                source="mqtt",
                synced_to_gcp=False
            ),
        ]

        mock_db.get_unsynced_events.return_value = events
        gcp_uploader.client.insert_rows_json.return_value = []

        count = gcp_uploader.upload_events()

        assert count == 2
        gcp_uploader.client.insert_rows_json.assert_called_once()
        mock_db.mark_synced.assert_called_once()

    def test_upload_events_with_errors(self, gcp_uploader, mock_db):
        """Test event upload with BigQuery errors."""
        events = [
            Mock(id=1, timestamp=datetime.utcnow(), entity_id="light.test1",
                 event_type="state_changed", domain="light", state="on",
                 attributes=None, source="mqtt"),
        ]

        mock_db.get_unsynced_events.return_value = events
        gcp_uploader.client.insert_rows_json.return_value = [{"error": "Invalid"}]

        count = gcp_uploader.upload_events()

        assert count == 0
        mock_db.mark_sync_failed.assert_called_once()

    def test_upload_events_batch_size(self, gcp_uploader, mock_db):
        """Test upload respects batch size limit."""
        events = [Mock(id=i, timestamp=datetime.utcnow(),
                      entity_id=f"light.test{i}", event_type="state_changed",
                      domain="light", state="on", attributes=None, source="mqtt")
                 for i in range(10)]

        mock_db.get_unsynced_events.return_value = events
        gcp_uploader.client.insert_rows_json.return_value = []

        count = gcp_uploader.upload_events(batch_size=5)

        assert count == 5

    def test_event_to_bq_row_conversion(self, gcp_uploader):
        """Test event to BigQuery row conversion."""
        event = Mock(
            id=1,
            timestamp=datetime(2026, 3, 1, 12, 0, 0),
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on",
            attributes='{"brightness": 255}',
            source="mqtt"
        )

        row = gcp_uploader._event_to_bq_row(event)

        assert row["id"] == 1
        assert row["entity_id"] == "light.test"
        assert row["event_type"] == "state_changed"
        assert row["domain"] == "light"
        assert row["state"] == "on"
        assert row["source"] == "mqtt"
        assert "ingested_at" in row

    def test_event_to_bq_row_with_null_attributes(self, gcp_uploader):
        """Test event to BigQuery row with null attributes."""
        event = Mock(
            id=1,
            timestamp=datetime.utcnow(),
            entity_id="sensor.test",
            event_type="state_changed",
            domain="sensor",
            state="25.5",
            attributes=None,
            source="mqtt"
        )

        row = gcp_uploader._event_to_bq_row(event)

        assert row["attributes"] == "{}"

    def test_event_to_bq_row_with_invalid_json(self, gcp_uploader):
        """Test event to BigQuery row with invalid JSON attributes."""
        event = Mock(
            id=1,
            timestamp=datetime.utcnow(),
            entity_id="light.test",
            event_type="state_changed",
            domain="light",
            state="on",
            attributes="invalid json",
            source="mqtt"
        )

        row = gcp_uploader._event_to_bq_row(event)

        # Should handle gracefully
        assert "attributes" in row

    def test_upload_events_exception_handling(self, gcp_uploader, mock_db):
        """Test error handling in upload_events."""
        events = [Mock(id=1)]
        mock_db.get_unsynced_events.return_value = events
        gcp_uploader.client.insert_rows_json.side_effect = Exception("API Error")

        with pytest.raises(GCPSyncError):
            gcp_uploader.upload_events()

    def test_uploader_disabled(self, mock_db):
        """Test uploader behavior when GCP sync is disabled."""
        with patch('ha_event_processor.gcp.settings') as mock_settings:
            mock_settings.enable_gcp_sync = False
            mock_settings.max_retries = 3
            mock_settings.event_retention_days = 30

            uploader = GCPUploader(mock_db)
            assert uploader.client is None

    def test_upload_empty_batch(self, gcp_uploader, mock_db):
        """Test uploading empty batch."""
        mock_db.get_unsynced_events.return_value = []

        count = gcp_uploader.upload_events()

        assert count == 0

    def test_table_id_formatting(self, gcp_uploader):
        """Test BigQuery table ID is properly formatted."""
        assert gcp_uploader.table_id == "test-project.test_dataset.events"
        assert "." in gcp_uploader.table_id
        parts = gcp_uploader.table_id.split(".")
        assert len(parts) == 3

    def test_multiple_uploads(self, gcp_uploader, mock_db):
        """Test multiple sequential uploads."""
        events = [Mock(id=1, timestamp=datetime.utcnow(),
                      entity_id="light.test", event_type="state_changed",
                      domain="light", state="on", attributes=None, source="mqtt")]

        mock_db.get_unsynced_events.return_value = events
        gcp_uploader.client.insert_rows_json.return_value = []

        # First upload
        count1 = gcp_uploader.upload_events()
        assert count1 == 1

        # Second upload (no events)
        mock_db.get_unsynced_events.return_value = []
        count2 = gcp_uploader.upload_events()
        assert count2 == 0

