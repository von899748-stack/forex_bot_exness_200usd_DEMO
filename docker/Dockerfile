# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -e .

# Create directories
RUN mkdir -p logs data/historical

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Run bot (default command can be overridden)
CMD ["python", "-m", "src.main", "--mode", "demo"]
