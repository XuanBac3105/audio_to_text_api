FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install (also install gunicorn)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt gunicorn

# Copy application
COPY . /app

# Create runtime dirs
RUN mkdir -p /tmp/uploads /tmp/outputs

EXPOSE 5000

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--workers", "1"]
