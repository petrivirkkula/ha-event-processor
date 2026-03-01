"""Database access layer for Home Assistant events."""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..config import settings
from ..exceptions import StorageError
from .models import Base, Event

logger = logging.getLogger(__name__)


def _safe_int(value, default: int) -> int:
    """Safely coerce a value to int, falling back to default on errors.

    This prevents passing MagicMock or other unsupported types into SQLAlchemy
    queries which would raise sqlite3.ProgrammingError during parameter
    binding.
    """
    try:
        if isinstance(value, int):
            return value
        # Try to coerce (handles str digits)
        return int(value)
    except Exception:
        return default


class Database:
    """Database management class."""

    def __init__(self):
        """Initialize database connection."""
        try:
            # Use StaticPool for SQLite to ensure compatibility in containers
            kwargs = {}
            if settings.database_url.startswith("sqlite"):
                kwargs["connect_args"] = {"check_same_thread": False}
                kwargs["poolclass"] = StaticPool
            else:
                kwargs["pool_size"] = settings.database_pool_size
                kwargs["pool_recycle"] = 3600

            self.engine = create_engine(settings.database_url, **kwargs)
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            # Create tables
            Base.metadata.create_all(bind=self.engine)
            logger.info(f"Database initialized: {settings.database_url}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise StorageError(f"Database initialization failed: {e}")

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def add_event(
        self,
        entity_id: str,
        event_type: str,
        domain: str,
        state: Optional[str] = None,
        attributes: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        service: Optional[str] = None,
        raw_payload: Optional[str] = None,
    ) -> Event:
        """Add an event to the database."""
        session = self.get_session()
        try:
            event = Event(
                entity_id=entity_id,
                event_type=event_type,
                domain=domain,
                state=state,
                attributes=attributes,
                timestamp=timestamp or datetime.utcnow(),
                service=service,
                raw_payload=raw_payload,
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            logger.debug(f"Event stored: {event.id} ({entity_id})")
            return event
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store event: {e}")
            raise StorageError(f"Failed to store event: {e}")
        finally:
            session.close()

    def get_unsynced_events(self, limit: int = 100) -> List[Event]:
        """Get events that haven't been synced to GCP."""
        session = self.get_session()
        try:
            max_retries = _safe_int(getattr(settings, "max_retries", 3), 3)
            events = (
                session.query(Event)
                .filter(Event.synced_to_gcp == False)
                .filter(Event.retry_count < max_retries)
                .order_by(Event.timestamp.asc())
                .limit(limit)
                .all()
            )
            logger.debug(f"Retrieved {len(events)} unsynced events")
            return events
        except Exception as e:
            logger.error(f"Failed to retrieve unsynced events: {e}")
            raise StorageError(f"Failed to retrieve unsynced events: {e}")
        finally:
            session.close()

    def mark_synced(self, event_ids: List[int]) -> None:
        """Mark events as synced to GCP."""
        session = self.get_session()
        try:
            session.query(Event).filter(Event.id.in_(event_ids)).update(
                {
                    Event.synced_to_gcp: True,
                    Event.sync_timestamp: datetime.utcnow(),
                    Event.sync_error: None,
                }
            )
            session.commit()
            logger.debug(f"Marked {len(event_ids)} events as synced")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to mark events as synced: {e}")
            raise StorageError(f"Failed to mark events as synced: {e}")
        finally:
            session.close()

    def mark_sync_failed(self, event_id: int, error_message: str) -> None:
        """Mark an event as failed sync."""
        session = self.get_session()
        try:
            event = session.query(Event).filter(Event.id == event_id).first()
            if event:
                event.retry_count += 1
                event.sync_error = error_message
                session.commit()
                logger.debug(f"Event {event_id} sync failed: {error_message}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to mark event sync failure: {e}")
            raise StorageError(f"Failed to mark event sync failure: {e}")
        finally:
            session.close()

    def cleanup_old_events(self, days: int = None) -> int:
        """Delete events older than specified days."""
        days = days or _safe_int(getattr(settings, "event_retention_days", 30), 30)
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = session.query(Event).filter(Event.timestamp < cutoff_date).delete()
            session.commit()
            logger.info(f"Cleaned up {result} old events (older than {days} days)")
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to cleanup old events: {e}")
            raise StorageError(f"Failed to cleanup old events: {e}")
        finally:
            session.close()

    def get_event_count(self, synced: Optional[bool] = None) -> int:
        """Get total event count."""
        session = self.get_session()
        try:
            query = session.query(Event)
            if synced is not None:
                query = query.filter(Event.synced_to_gcp == synced)
            count = query.count()
            return count
        except Exception as e:
            logger.error(f"Failed to get event count: {e}")
            raise StorageError(f"Failed to get event count: {e}")
        finally:
            session.close()

    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()
        logger.info("Database connection closed")


# Global database instance
db: Optional[Database] = None


def get_db() -> Database:
    """Get or initialize database instance."""
    global db
    if db is None:
        db = Database()
    return db

