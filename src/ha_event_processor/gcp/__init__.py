"""Google Cloud integration for event synchronization."""
import json
import logging
import os
from typing import List, Optional
from datetime import datetime
import tempfile

from google.cloud import bigquery
from google.oauth2 import service_account

from ..config import settings
from ..exceptions import GCPSyncError, ConfigurationError
from ..storage.database import Database
from ..storage.models import Event

logger = logging.getLogger(__name__)


class GCPUploader:
    """Upload events to Google Cloud BigQuery."""

    def __init__(self, database: Database):
        """Initialize GCP uploader.

        Args:
            database: Database instance

        Raises:
            ConfigurationError: If GCP configuration is invalid
        """
        self.database = database
        self.client = None
        self.table_id = (
            f"{settings.gcp_project_id}.{settings.gcp_dataset_id}."
            f"{settings.gcp_table_id}"
        )

        if settings.enable_gcp_sync:
            self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize BigQuery client.

        Raises:
            ConfigurationError: If authentication fails
        """
        try:
            if not settings.gcp_project_id:
                raise ConfigurationError("GCP_PROJECT_ID is not set")

            # Try to use service account JSON if provided
            if settings.gcp_service_account_json:
                # Create temporary file with service account JSON
                with tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".json"
                ) as f:
                    f.write(settings.gcp_service_account_json)
                    temp_file = f.name

                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        temp_file,
                        scopes=[
                            "https://www.googleapis.com/auth/bigquery",
                            "https://www.googleapis.com/auth/cloud-platform",
                        ],
                    )
                    self.client = bigquery.Client(
                        project=settings.gcp_project_id, credentials=credentials
                    )
                finally:
                    os.unlink(temp_file)
            else:
                # Try to use default credentials
                self.client = bigquery.Client(project=settings.gcp_project_id)

            logger.info(f"Connected to BigQuery: {self.table_id}")
            self._ensure_dataset_and_table()

        except ConfigurationError:
            raise
        except Exception as e:
            logger.error(f"Failed to initialize GCP client: {e}")
            raise ConfigurationError(f"GCP initialization failed: {e}")

    def _ensure_dataset_and_table(self) -> None:
        """Ensure dataset and table exist."""
        try:
            dataset_id = f"{settings.gcp_project_id}.{settings.gcp_dataset_id}"
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"

            try:
                self.client.get_dataset(dataset_id)
                logger.info(f"Dataset exists: {dataset_id}")
            except Exception:
                self.client.create_dataset(dataset, exists_ok=True)
                logger.info(f"Created dataset: {dataset_id}")

            # Check/create table
            table = self.client.get_table(self.table_id)
            logger.info(f"Table exists: {self.table_id}")

        except Exception as e:
            logger.warning(f"Could not verify dataset/table: {e}")
            # Continue anyway - table might be created during first insert

    def upload_events(self, batch_size: Optional[int] = None) -> int:
        """Upload unsynced events to BigQuery.

        Args:
            batch_size: Number of events to upload per batch

        Returns:
            Number of events uploaded
        """
        if not self.client:
            logger.warning("GCP client not initialized, skipping upload")
            return 0

        batch_size = batch_size or settings.gcp_batch_size
        uploaded_count = 0

        try:
            # Get unsynced events
            events = self.database.get_unsynced_events(limit=batch_size)
            if not events:
                logger.debug("No unsynced events to upload")
                return 0

            # Defensive: if the database returned more events than requested,
            # respect the batch_size parameter by trimming the list. This
            # prevents unexpected behavior when tests or mocks return more
            # items than the limit argument was supposed to enforce.
            if batch_size is not None and len(events) > batch_size:
                logger.debug(
                    f"Database returned {len(events)} events, trimming to batch_size={batch_size}"
                )
                events = events[:batch_size]

            # Convert events to BigQuery format
            rows = [self._event_to_bq_row(event) for event in events]

            # Insert into BigQuery
            errors = self.client.insert_rows_json(self.table_id, rows)

            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
                # Mark individual events as failed
                for event in events:
                    self.database.mark_sync_failed(
                        event.id, f"BigQuery insert error: {errors[0]}"
                    )
            else:
                # Mark all events as synced
                event_ids = [event.id for event in events]
                self.database.mark_synced(event_ids)
                uploaded_count = len(event_ids)
                logger.info(f"Uploaded {uploaded_count} events to BigQuery")

        except Exception as e:
            logger.error(f"Failed to upload events to BigQuery: {e}")
            raise GCPSyncError(f"BigQuery upload failed: {e}")

        return uploaded_count

    def _event_to_bq_row(self, event: Event) -> dict:
        """Convert event to BigQuery row format.

        Args:
            event: Event model instance

        Returns:
            Dictionary suitable for BigQuery insertion
        """
        # Parse attributes if JSON string
        attributes = {}
        if event.attributes:
            try:
                attributes = json.loads(event.attributes)
            except json.JSONDecodeError:
                attributes = {"raw": event.attributes}

        return {
            "id": event.id,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "entity_id": event.entity_id,
            "event_type": event.event_type,
            "domain": event.domain,
            "state": event.state,
            "attributes": json.dumps(attributes),
            "source": event.source,
            "ingested_at": datetime.utcnow().isoformat(),
        }
