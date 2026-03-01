# HA Event Processor - Project Summary

## Overview
The ha-event-processor is a production-ready Python application designed to run in k3s (lightweight Kubernetes) clusters. It subscribes to Home Assistant MQTT events, stores them locally in a database, and syncs them to Google Cloud BigQuery for machine learning model training.

## Project Structure

```
ha-event-processor/
├── src/
│   ├── main.py                          # FastAPI application entry point
│   └── ha-event-processor/              # Main package
│       ├── __init__.py
│       ├── config/
│       │   └── __init__.py             # Settings management (Pydantic)
│       ├── events/
│       │   ├── __init__.py
│       │   └── processor.py            # Event validation & processing
│       ├── mqtt/
│       │   ├── __init__.py
│       │   └── client.py               # MQTT client (paho-mqtt)
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py             # SQLAlchemy database layer
│       │   └── models.py               # SQLAlchemy event model
│       ├── gcp/
│       │   └── __init__.py             # Google Cloud BigQuery integration
│       ├── monitoring/
│       │   └── __init__.py             # Prometheus metrics
│       └── exceptions.py               # Custom exceptions
├── k3s/
│   ├── deployment.yaml                 # Kubernetes Deployment
│   ├── service.yaml                    # Kubernetes Service
│   ├── configmap.yaml                  # Configuration
│   ├── secret.yaml                     # Credentials (MQTT, GCP)
│   ├── pvc.yaml                        # PersistentVolumeClaim
│   └── rbac.yaml                       # ServiceAccount + RBAC
├── scripts/
│   └── deploy.sh                       # k3s deployment helper script
├── Dockerfile                          # Multi-stage Docker image
├── docker-compose.yml                  # Local development stack
├── requirements.txt                    # Python dependencies
├── .env.example                        # Environment variables template
├── .gitignore                          # Git ignore rules
└── README.md                           # Full documentation
```

## Key Components

### 1. MQTT Client (`mqtt/client.py`)
- Connects to MQTT broker (configurable)
- Subscribes to Home Assistant state topics
- Parses and validates events
- Handles reconnection with exponential backoff
- Passes events to processor

### 2. Event Processor (`events/processor.py`)
- Validates event data structure
- Normalizes entity_id format
- Parses state and attributes
- Stores validated events in database

### 3. Database Layer (`storage/`)
- SQLAlchemy ORM for database abstraction
- SQLite (development) or PostgreSQL (production)
- Models: Event with sync tracking
- Operations: store, retrieve, mark synced, cleanup old events
- Connection pooling and error handling

### 4. GCP Uploader (`gcp/__init__.py`)
- BigQuery integration using google-cloud-bigquery
- Batch processing for cost efficiency
- Automatic schema creation
- Retry logic with exponential backoff
- Service account authentication

### 5. Monitoring (`monitoring/`)
- Prometheus metrics
- Event counters (received, stored, synced)
- Connection status gauges
- Processing time histograms

### 6. Configuration (`config/`)
- Pydantic-based settings
- Environment variable loading
- Support for .env file
- Runtime validation

### 7. FastAPI Application (`main.py`)
- RESTful API endpoints
- Health check endpoint (/health)
- Statistics endpoint (/stats)
- Prometheus metrics endpoint (/metrics)
- Manual sync trigger (/sync)
- Graceful startup/shutdown
- Background task for periodic syncing

## Configuration

### Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `MQTT_BROKER_HOST` | localhost | MQTT broker address |
| `MQTT_BROKER_PORT` | 1883 | MQTT broker port |
| `MQTT_USERNAME` | - | MQTT authentication |
| `MQTT_PASSWORD` | - | MQTT authentication |
| `DATABASE_URL` | sqlite:///ha_events.db | Database connection |
| `GCP_PROJECT_ID` | - | Google Cloud project ID |
| `GCP_DATASET_ID` | ha_events | BigQuery dataset |
| `GCP_TABLE_ID` | events | BigQuery table |
| `ENABLE_GCP_SYNC` | true | Enable/disable GCP upload |
| `EVENT_RETENTION_DAYS` | 30 | Days to keep events |
| `LOG_LEVEL` | INFO | Logging verbosity |

## Deployment

### Local Development
```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your MQTT broker

# Run
python src/main.py
```

### Docker Compose
```bash
docker-compose up
```
Includes MQTT broker, processor, and optional PostgreSQL.

### k3s Deployment
```bash
# Update configuration
vim k3s/configmap.yaml
vim k3s/secret.yaml

# Deploy
kubectl apply -f k3s/

# Or use helper script
bash scripts/deploy.sh
```

## API Endpoints

### Health Check
```bash
GET /health
# Returns connection status and configuration
```

### Statistics
```bash
GET /stats
# Returns event counts and sync status
```

### Prometheus Metrics
```bash
GET /metrics
# Returns Prometheus-compatible metrics
```

### Manual Sync
```bash
POST /sync
# Manually trigger GCP sync
```

## Data Flow

1. **MQTT → Event Processor**
   - Subscribe to `homeassistant/#`
   - Parse topic and payload
   - Validate event structure

2. **Event Processor → Database**
   - Normalize entity_id (domain.entity)
   - Extract state and attributes
   - Store with timestamp
   - Mark as unsynced

3. **Database → GCP Uploader**
   - Background task checks for unsynced events
   - Batch events (default: 100)
   - Upload to BigQuery
   - Mark as synced on success

4. **GCP → BigQuery**
   - Events table with schema
   - Available for ML model training
   - Query-able with SQL

## Security Features

- Non-root container user (UID 1000)
- Kubernetes RBAC with minimal permissions
- Secret management for sensitive data
- Health checks and resource limits
- Graceful shutdown on signals
- Request validation

## Monitoring

### Health Checks
- Liveness probe: `/health` endpoint
- Readiness probe: checks MQTT connection
- Container restart on failure

### Metrics
- Prometheus-compatible metrics
- Integration with monitoring systems
- Event processing latency
- Sync success/failure rates
- Connection status

### Logging
- Structured logging with timestamps
- Configurable log levels
- Module-level loggers
- Error tracking and debugging info

## Database Schema

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    entity_id VARCHAR(255),
    event_type VARCHAR(255),
    domain VARCHAR(255),
    state VARCHAR(255),
    attributes TEXT,  -- JSON
    synced_to_gcp BOOLEAN,
    sync_timestamp DATETIME,
    sync_error TEXT,
    retry_count INTEGER,
    source VARCHAR(255),
    raw_payload TEXT,
    created_at DATETIME,
    updated_at DATETIME
);

-- BigQuery compatible schema
id
timestamp
entity_id
event_type
domain
state
attributes (JSON)
source
ingested_at
```

## Dependencies

### Core
- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **pydantic**: Settings validation

### MQTT
- **paho-mqtt**: MQTT client library

### Database
- **sqlalchemy**: ORM and database toolkit

### Google Cloud
- **google-cloud-bigquery**: BigQuery client

### Monitoring
- **prometheus-client**: Metrics

### Configuration
- **python-dotenv**: .env file support

## Performance Tuning

### Database
- `DATABASE_POOL_SIZE`: Connection pool size (default: 5)
- Connection recycling: 3600 seconds

### GCP Sync
- `GCP_BATCH_SIZE`: Events per batch (default: 100)
- `GCP_BATCH_TIMEOUT_SECONDS`: Flush interval (default: 300)
- Exponential backoff for retries

### Kubernetes
- Memory requests: 128Mi, limits: 512Mi
- CPU requests: 100m, limits: 500m
- Storage: 10Gi PVC

## Troubleshooting

### MQTT Connection Issues
- Check broker host/port
- Verify network connectivity
- Check credentials
- View logs: `kubectl logs -f deployment/ha-event-processor`

### Database Issues
- Check SQLite file permissions
- Verify PostgreSQL connection string
- Check disk space
- Review database logs

### GCP Sync Issues
- Verify service account permissions
- Check project ID
- Verify dataset/table exist
- Check GCP credentials JSON

## Next Steps

1. **Build Docker image**: `docker build -t ha-event-processor:latest .`
2. **Push to registry**: Docker Hub, ECR, GCR, etc.
3. **Update k3s/deployment.yaml** with image registry
4. **Deploy to k3s**: `kubectl apply -f k3s/`
5. **Monitor**: `kubectl logs -f deployment/ha-event-processor`
6. **Verify**: `curl http://pod-ip:8000/health`

## Support & Documentation

- See `README.md` for detailed deployment instructions
- See `requirements.txt` for exact versions
- See `.env.example` for all configuration options
- See `k3s/*.yaml` for Kubernetes manifests

## License

MIT License

