FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc nodejs npm imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy app code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI
CMD ["sh", "-c", "alembic upgrade head && uvicorn ui_server.app:app --host 0.0.0.0 --port 8000"]