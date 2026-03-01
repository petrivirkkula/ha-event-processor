"""Multi-stage Dockerfile for HA Event Processor."""

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim

# Set labels
LABEL maintainer="ha-event-processor"
LABEL description="Home Assistant event processor for k3s"
LABEL version="1.0.0"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 processor

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVER_HOST="0.0.0.0" \
    SERVER_PORT="8000" \
    LOG_LEVEL="INFO"

# Create app directory
WORKDIR /app

# Copy application code
COPY --chown=processor:processor src/ha-event-processor /app/ha_event_processor
COPY --chown=processor:processor src/main.py /app/

# Create data directory for database
RUN mkdir -p /app/data && chown -R processor:processor /app/data

# Switch to non-root user
USER processor

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

