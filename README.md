# HA Event Processor

A production-ready Home Assistant event processor that runs in k3s, receives events from MQTT, stores them locally, and syncs them to Google Cloud BigQuery for model training.

## Features

- **MQTT Integration**: Subscribes to Home Assistant MQTT events
- **Local Storage**: SQLite or PostgreSQL for persistent event storage
- **Google Cloud Sync**: Batch uploads events to BigQuery for ML model training
- **k3s Ready**: Kubernetes manifests included for easy deployment
- **Health Checks**: Liveness and readiness probes for monitoring
- **Metrics**: Prometheus-compatible metrics endpoint
- **Retry Logic**: Exponential backoff for failed sync attempts
- **Event Cleanup**: Automatic deletion of old events based on retention policy
- **Graceful Shutdown**: Proper signal handling and resource cleanup

## Architecture

```
MQTT Broker (Home Assistant)
    ↓
MQTT Client (paho-mqtt)
    ↓
Event Processor (validation & normalization)
    ↓
Local Database (SQLite/PostgreSQL)
    ↓
GCP Uploader (BigQuery batch insert)
    ↓
Google Cloud BigQuery
```

## Components

### mqtt/client.py
Handles MQTT connection and message parsing. Subscribes to Home Assistant state topics and converts them to events.

### events/processor.py
Validates and normalizes incoming events before storage. Ensures data consistency and quality.

### storage/database.py & storage/models.py
Manages SQLite/PostgreSQL database operations. Stores events with sync status tracking for retry logic.

### gcp/__init__.py
BigQuery uploader that batches events and syncs them to Google Cloud for training datasets.

### config/
Settings management using Pydantic, loading from environment variables and `.env` file.

### monitoring/
Prometheus metrics for observability (event counts, processing time, sync status).

## Quick Start

### Local Development

1. **Clone and setup:**
   ```bash
   cd ha_event_processor
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your MQTT broker details
   ```

3. **Run application:**
   ```bash
   python src/main.py
   ```

4. **Check health:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/stats
   ```

### Docker Build

```bash
docker build -t ha_event_processor:latest .
docker run -p 8000:8000 \
  -e MQTT_BROKER_HOST=host.docker.internal \
  -e GCP_PROJECT_ID=your-project \
  ha_event_processor:latest
```

### k3s Deployment

1. **Update configuration:**
   ```bash
   # Edit k3s/configmap.yaml with your MQTT broker and GCP project
   vim k3s/configmap.yaml
   ```

2. **Configure secrets:**
   ```bash
   # Encode MQTT credentials and GCP service account JSON
   echo -n "your-username" | base64
   cat gcp-service-account.json | base64
   
   # Update k3s/secret.yaml with base64-encoded values
   vim k3s/secret.yaml
   ```

3. **Deploy to k3s:**
   ```bash
   # Apply all manifests
   kubectl apply -f k3s/rbac.yaml
   kubectl apply -f k3s/configmap.yaml
   kubectl apply -f k3s/secret.yaml
   kubectl apply -f k3s/pvc.yaml
   kubectl apply -f k3s/service.yaml
   kubectl apply -f k3s/deployment.yaml
   
   # Or deploy all at once:
   kubectl apply -f k3s/
   ```

4. **Monitor deployment:**
   ```bash
   # Watch pod status
   kubectl get pods -w
   
   # View logs
   kubectl logs -f deployment/ha_event_processor
   
   # Check service
   kubectl get svc ha_event_processor
   kubectl port-forward svc/ha_event_processor 8000:8000
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER_HOST` | localhost | MQTT broker hostname |
| `MQTT_BROKER_PORT` | 1883 | MQTT broker port |
| `MQTT_USERNAME` | - | MQTT username (optional) |
| `MQTT_PASSWORD` | - | MQTT password (optional) |
| `MQTT_CLIENT_ID` | ha-event-processor | MQTT client ID |
| `DATABASE_URL` | sqlite:///ha_events.db | Database connection string |
| `GCP_PROJECT_ID` | - | Google Cloud project ID |
| `GCP_DATASET_ID` | ha_events | BigQuery dataset name |
| `GCP_TABLE_ID` | events | BigQuery table name |
| `ENABLE_GCP_SYNC` | true | Enable/disable GCP synchronization |
| `EVENT_RETENTION_DAYS` | 30 | Days to keep events before cleanup |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Database Setup

**SQLite** (default, development):
```bash
# Already created automatically
DATABASE_URL=sqlite:///./ha_events.db
```

**PostgreSQL** (production):
```bash
# Install PostgreSQL client library
pip install psycopg2-binary

# Update database URL
DATABASE_URL=postgresql://user:password@postgres-host:5432/ha_events
```

### Google Cloud Setup

1. **Create a service account:**
   ```bash
   gcloud iam service-accounts create ha_event_processor
   gcloud projects add-iam-policy-binding YOUR_PROJECT \
     --member=serviceAccount:ha_event_processor@YOUR_PROJECT.iam.gserviceaccount.com \
     --role=roles/bigquery.dataEditor
   ```

2. **Create and download key:**
   ```bash
   gcloud iam service-accounts keys create sa-key.json \
     --iam-account=ha_event_processor@YOUR_PROJECT.iam.gserviceaccount.com
   ```

3. **Set in k3s secret or environment:**
   ```bash
   export GCP_SERVICE_ACCOUNT_JSON=$(cat sa-key.json)
   # Or base64 encode and add to k3s/secret.yaml
   ```

4. **Create schema.json With Following Content**
   ```json
   [
     {
       "mode": "REQUIRED",
       "name": "id",
       "type": "INTEGER"
     },
     {
       "mode": "REQUIRED",
       "name": "timestamp",
       "type": "TIMESTAMP"
     },
     {
       "maxLength": "255",
       "mode": "REQUIRED",
       "name": "entity_id",
       "type": "STRING"
     },
     {
       "maxLength": "255",
       "mode": "REQUIRED",
       "name": "event_type",
       "type": "STRING"
     },
     {
       "maxLength": "255",
       "mode": "NULLABLE",
       "name": "domain",
       "type": "STRING"
     },
     {
       "maxLength": "255",
       "mode": "NULLABLE",
       "name": "state",
       "type": "STRING"
     },
     {
       "mode": "NULLABLE",
       "name": "attributes",
       "type": "STRING"
     },
     {
       "defaultValueExpression": "\"mqtt\"",
       "maxLength": "255",
       "mode": "REQUIRED",
       "name": "source",
       "type": "STRING"
     },
     {
       "mode": "REQUIRED",
       "name": "ingested_at",
       "type": "TIMESTAMP"
     }
   ]
   ```

5. **Create BigQuery table From The Schema File:**
   ```bash
   bq mk --table YOUR_PROJECT:YOUR_DATASET.YOUR_TABLE scheem.json
   ```

   Other option is to use GCP Console to create the table but the there is no JSON option in the Console


## API Endpoints

### Health Check
```bash
GET /health
# Returns: {"status": "healthy", "mqtt_connected": true, "gcp_enabled": true}
```

### Statistics
```bash
GET /stats
# Returns: {
#   "total_events": 1234,
#   "pending_events": 5,
#   "synced_events": 1229,
#   "mqtt_connected": true,
#   "gcp_enabled": true
# }
```

### Prometheus Metrics
```bash
GET /metrics
# Prometheus-compatible metrics output
```

### Manual Sync Trigger
```bash
POST /sync
# Returns: {"synced_count": 100}
```

## Metrics

Available Prometheus metrics:

- `ha_events_received_total` - Total events received from MQTT
- `ha_events_stored_total` - Total events stored in database
- `ha_events_synced_total` - Total events synced to GCP
- `ha_sync_errors_total` - Total sync errors
- `ha_events_pending_total` - Pending events to sync
- `ha_mqtt_connected` - MQTT connection status (0/1)
- `ha_gcp_connected` - GCP connection status (0/1)
- `ha_event_processing_duration_seconds` - Event processing time histogram
- `ha_gcp_sync_duration_seconds` - GCP sync time histogram

## Event Schema

Events stored in the database follow this structure:

```python
{
    "id": 1,
    "timestamp": "2024-03-01T12:00:00Z",
    "entity_id": "light.living_room",
    "event_type": "state_changed",
    "domain": "light",
    "state": "on",
    "attributes": {"brightness": 255, "color_temp": 3000},
    "synced_to_gcp": true,
    "sync_timestamp": "2024-03-01T12:01:00Z",
    "source": "mqtt"
}
```

BigQuery table schema is automatically created on first sync.

## Troubleshooting

### MQTT Connection Issues
```bash
# Check MQTT connectivity
kubectl exec -it deployment/ha_event_processor -- \
  python -c "import paho.mqtt.client as mqtt; print('MQTT library OK')"

# View logs
kubectl logs -f deployment/ha_event_processor | grep -i mqtt
```

### Database Issues
```bash
# Check database file exists and is readable
kubectl exec -it deployment/ha_event_processor -- \
  ls -la /app/data/

# Check SQLite database
kubectl exec -it deployment/ha_event_processor -- \
  sqlite3 /app/data/ha_events.db ".tables"
```

### GCP Sync Issues
```bash
# Check GCP credentials
kubectl exec -it deployment/ha_event_processor -- \
  python -c "from google.cloud import bigquery; print('GCP OK')"

# View sync logs
kubectl logs -f deployment/ha_event_processor | grep -i gcp
```

### Check Pod Status
```bash
# View pod details
kubectl describe pod <pod-name>

# Check events
kubectl get events --sort-by='.lastTimestamp'
```

## Performance Tuning

### Database Connection Pool
```yaml
DATABASE_POOL_SIZE: "10"  # Increase for high throughput
```

### GCP Batch Size
```yaml
GCP_BATCH_SIZE: "500"  # Larger batches = fewer API calls
GCP_BATCH_TIMEOUT_SECONDS: "60"  # Flush sooner for lower latency
```

### Resource Limits
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

## Development

### Running Tests
```bash
pip install pytest pytest-asyncio
pytest tests/
```

### Code Style
```bash
pip install black flake8
black src/
flake8 src/
```

### Type Checking
```bash
pip install mypy
mypy src/
```

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions:
- Check existing GitHub issues
- Create a new issue with details and logs
- Check logs: `kubectl logs -f deployment/ha-event-processor`

