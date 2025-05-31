# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    API_HOST=0.0.0.0 \
    API_PORT=5681 \
    API_WORKERS=4 \
    API_RELOAD=false \
    MAX_WORKERS=30 \
    INITIAL_RATE=30 \
    MIN_RATE=5 \
    MAX_RATE=50 \
    BACKOFF_FACTOR=1.5 \
    RECOVERY_FACTOR=0.8 \
    MAX_CONSECUTIVE_FAILURES=5 \
    LOG_LEVEL=info \
    ENABLE_ACCESS_LOG=true

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE ${API_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${API_PORT}/health || exit 1

# Command to run the application
CMD ["uvicorn", "fastapi_server:app", "--host", "0.0.0.0", "--port", "5681"] 