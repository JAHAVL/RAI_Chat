FROM python:3.10-slim

WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.docker.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.docker.txt

# Copy backend code
COPY . .

# Create data directory for SQLite and logs
RUN mkdir -p data/logs

# Set environment variables
ENV PYTHONPATH=/RAI_Chat_V1.3.1_20250408_1319PM:/app
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Expose the port the backend runs on
EXPOSE 6102

# Run the backend server using waitress for production-ready serving
CMD ["python", "wsgi.py"]
