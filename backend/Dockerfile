FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for some AI libraries if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend
COPY backend/app ./app
COPY backend/dark_crawler.py ./dark_crawler.py
COPY ai ./ai
COPY graph ./graph
COPY scripts ./scripts
COPY data ./data

# Set python path
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
