# ==============================
# FastAPI + Alembic Dockerfile
# ==============================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev git && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the app
COPY ./app ./app
COPY alembic.ini .
COPY .env .

# Expose FastAPI port
EXPOSE 8000

# Run Alembic migrations and start FastAPI
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
