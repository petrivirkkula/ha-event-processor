"""Database models for storing Home Assistant events."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Event(Base):
    """Home Assistant event model."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Event metadata
    entity_id = Column(String(255), index=True)
    event_type = Column(String(255), index=True)
    domain = Column(String(255), index=True)
    service = Column(String(255), nullable=True)

    # Event data
    state = Column(String(255), nullable=True)
    attributes = Column(Text, nullable=True)  # JSON string

    # Processing status
    synced_to_gcp = Column(Boolean, default=False, index=True)
    sync_timestamp = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Additional metadata
    source = Column(String(255), default="mqtt")
    raw_payload = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Event(id={self.id}, entity_id={self.entity_id}, "
            f"event_type={self.event_type}, timestamp={self.timestamp})>"
        )

