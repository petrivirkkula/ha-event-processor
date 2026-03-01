"""Main application for HA Event Processor."""
import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_client import REGISTRY, generate_latest

from ha_event_processor.config import settings
from ha_event_processor.mqtt.client import MQTTClient
from ha_event_processor.events.processor import EventProcessor
from ha_event_processor.gcp import GCPUploader
from ha_event_processor.storage.database import Database, get_db
from ha_event_processor.monitoring import (
    set_mqtt_connected,
    set_gcp_connected,
    set_pending_events,
)

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
mqtt_client: Optional[MQTTClient] = None
event_processor: Optional[EventProcessor] = None
gcp_uploader: Optional[GCPUploader] = None
db: Optional[Database] = None
sync_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global mqtt_client, event_processor, gcp_uploader, db, sync_task

    # Startup
    logger.info("Starting HA Event Processor")

    # Initialize database
    db = get_db()

    # Initialize event processor
    event_processor = EventProcessor(db)

    # Initialize GCP uploader
    try:
        gcp_uploader = GCPUploader(db)
        set_gcp_connected(settings.enable_gcp_sync)
    except Exception as e:
        logger.warning(f"GCP initialization failed: {e}")
        gcp_uploader = None
        set_gcp_connected(False)

    # Initialize MQTT client
    try:
        mqtt_client = MQTTClient(on_message_callback=_on_mqtt_message)
        mqtt_client.connect()
        set_mqtt_connected(True)
    except Exception as e:
        logger.error(f"MQTT initialization failed: {e}")
        set_mqtt_connected(False)

    # Start background sync task
    sync_task = asyncio.create_task(_sync_events_loop())

    # Handle signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    yield

    # Shutdown
    logger.info("Shutting down HA Event Processor")

    # Cancel sync task
    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass

    # Disconnect MQTT
    if mqtt_client:
        mqtt_client.disconnect()

    # Close database
    if db:
        db.close()

    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="HA Event Processor",
    description="Home Assistant event processor with k3s support",
    version="1.0.0",
    lifespan=lifespan,
)


def _on_mqtt_message(event_data: dict) -> None:
    """Handle MQTT message callback.

    Args:
        event_data: Event data from MQTT
    """
    global event_processor

    if event_processor:
        event_processor.process_event(event_data)


async def _sync_events_loop() -> None:
    """Background task to sync events to GCP."""
    global gcp_uploader, db

    while True:
        try:
            await asyncio.sleep(settings.gcp_batch_timeout_seconds)

            if gcp_uploader and settings.enable_gcp_sync:
                logger.debug("Running scheduled GCP sync")
                try:
                    gcp_uploader.upload_events()
                except Exception as e:
                    logger.error(f"GCP sync failed: {e}")

            # Update pending events metric
            if db:
                pending_count = db.get_event_count(synced=False)
                set_pending_events(pending_count)

            # Cleanup old events
            if db:
                db.cleanup_old_events()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in sync loop: {e}")
            await asyncio.sleep(5)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    global mqtt_client, gcp_uploader

    health_status = {
        "status": "healthy",
        "mqtt_connected": mqtt_client.is_connected if mqtt_client else False,
        "gcp_enabled": settings.enable_gcp_sync,
    }

    if not health_status["mqtt_connected"]:
        health_status["status"] = "degraded"

    return JSONResponse(
        content=health_status,
        status_code=200 if health_status["status"] == "healthy" else 503,
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return app.openapi()(generate_latest(REGISTRY).decode("utf-8"))


@app.get("/stats")
async def stats():
    """Application statistics endpoint."""
    global db

    if not db:
        return {"error": "Database not initialized"}

    return {
        "total_events": db.get_event_count(),
        "pending_events": db.get_event_count(synced=False),
        "synced_events": db.get_event_count(synced=True),
        "mqtt_connected": mqtt_client.is_connected if mqtt_client else False,
        "gcp_enabled": settings.enable_gcp_sync,
    }


@app.post("/sync")
async def trigger_sync():
    """Manually trigger GCP sync."""
    global gcp_uploader

    if not gcp_uploader:
        return {"error": "GCP uploader not initialized"}

    try:
        count = gcp_uploader.upload_events()
        return {"synced_count": count}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
    )
