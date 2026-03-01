# HA Event Processor - Quick Start Guide

## 5-Minute Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (optional)
- kubectl (for k3s deployment)
- MQTT broker (e.g., Home Assistant's built-in MQTT addon)

---

## Option 1: Local Development (Fastest)

### 1. Install dependencies
```bash
cd ha_event_processor
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and set your MQTT broker host
```

### 3. Run the application
```bash
python src/main.py
```

### 4. Test it
```bash
# In another terminal:
curl http://localhost:8000/health
curl http://localhost:8000/stats
```

**Done!** The application is now:
- ✅ Listening to MQTT events
- ✅ Storing events in SQLite database
- ✅ Ready to sync to GCP (when configured)

---

## Option 2: Docker Compose (Recommended for Testing)

### 1. Start all services
```bash
docker-compose up
```

This will start:
- MQTT broker (Mosquitto)
- Event processor app
- Optional: PostgreSQL database

### 2. Test it
```bash
curl http://localhost:8000/health
curl http://localhost:8000/stats
```

### 3. Stop it
```bash
docker-compose down
```

---

## Option 3: k3s Deployment (Production)

### 1. Configure for your environment
```bash
# Edit k3s/configmap.yaml with your MQTT broker
# Edit k3s/secret.yaml with your credentials
vim k3s/configmap.yaml
vim k3s/secret.yaml
```

### 2. Deploy to k3s
```bash
# Option A: Manual deployment
kubectl apply -f k3s/

# Option B: Using helper script (interactive)
bash scripts/deploy.sh
```

### 3. Monitor deployment
```bash
# Watch pods
kubectl get pods -w

# View logs
kubectl logs -f deployment/ha_event_processor

# Port-forward to test
kubectl port-forward svc/ha_event_processor 8000:8000
```

### 4. Test
```bash
curl http://localhost:8000/health
```

---

## Configuration

### MQTT Connection
```env
MQTT_BROKER_HOST=your-mqtt-broker.local
MQTT_BROKER_PORT=1883
MQTT_USERNAME=user
MQTT_PASSWORD=password
```

### Google Cloud (Optional)
```env
ENABLE_GCP_SYNC=true
GCP_PROJECT_ID=your-gcp-project
GCP_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
```

### Database
```env
# SQLite (default)
DATABASE_URL=sqlite:///./ha_events.db

# PostgreSQL
DATABASE_URL=postgresql://user:pass@host:5432/ha_events
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check (liveness probe) |
| `/stats` | GET | Event statistics |
| `/metrics` | GET | Prometheus metrics |
| `/sync` | POST | Manual GCP sync trigger |

### Example Requests

```bash
# Health check
curl http://localhost:8000/health

# Get statistics
curl http://localhost:8000/stats

# Get metrics
curl http://localhost:8000/metrics

# Trigger manual sync
curl -X POST http://localhost:8000/sync
```

---

## Monitoring

### Check logs
```bash
# Local development
tail -f ha_events.db

# Docker Compose
docker-compose logs -f processor

# k3s
kubectl logs -f deployment/ha_event_processor
```

### Check database
```bash
# View event count
sqlite3 ha_events.db "SELECT COUNT(*) FROM events;"

# View pending events
sqlite3 ha_events.db "SELECT COUNT(*) FROM events WHERE synced_to_gcp = 0;"

# View recent events
sqlite3 ha_events.db "SELECT entity_id, state FROM events LIMIT 10;"
```

### Check MQTT connection
```bash
# Subscribe to test topic
mosquitto_sub -h your-mqtt-broker -t "homeassistant/#"
```

---

## Troubleshooting

### Application won't start
```bash
# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip install -r requirements.txt

# Check .env file exists
ls -la .env
```

### No events appearing
```bash
# Check MQTT connectivity
nc -zv your-mqtt-broker 1883

# Check MQTT credentials
mosquitto_sub -h your-mqtt-broker -u user -P pass -t "homeassistant/#"

# Check logs
python src/main.py 2>&1 | grep -i mqtt
```

### GCP sync not working
```bash
# Check GCP_PROJECT_ID is set
echo $GCP_PROJECT_ID

# Check service account file
cat $GCP_SERVICE_ACCOUNT_JSON | jq '.project_id'

# Test BigQuery connectivity
python -c "from google.cloud import bigquery; print('OK')"
```

---

## Next Steps

1. **Test MQTT connection**: Send a test event from Home Assistant
2. **Verify database**: Check events in SQLite database
3. **Set up GCP**: Create service account and enable BigQuery
4. **Configure monitoring**: Add Prometheus scrape config
5. **Deploy to production**: Push Docker image and deploy to k3s

---

## Important Files

- `README.md` - Full documentation
- `PROJECT_SUMMARY.md` - Architecture overview
- `.env.example` - Configuration template
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Local development setup
- `Dockerfile` - Container image definition
- `k3s/*.yaml` - Kubernetes manifests

---

## Support

For issues or questions:
1. Check logs: `kubectl logs deployment/ha-event-processor`
2. Review README.md troubleshooting section
3. Check .env configuration
4. Verify MQTT broker connectivity

---

## Quick Commands Reference

```bash
# Development
python src/main.py                    # Run locally
docker-compose up                     # Run with Docker
docker-compose down                   # Stop services

# k3s
kubectl apply -f k3s/                # Deploy
kubectl delete -f k3s/               # Uninstall
kubectl logs -f deployment/ha_event_processor  # View logs
kubectl port-forward svc/ha_event_processor 8000:8000  # Port forward

# Database
sqlite3 ha_events.db ".tables"       # List tables
sqlite3 ha_events.db "SELECT COUNT(*) FROM events;"  # Count events
sqlite3 ha_events.db "SELECT * FROM events LIMIT 5;" # View events
```

---

**You're all set!** 🎉

Start receiving Home Assistant events and syncing them to Google Cloud.

