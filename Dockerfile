FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for LightGBM execution (OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application backend and ADK agent source code
COPY backend/ ./backend/
COPY agents/ ./agents/
COPY datasets/ ./datasets/

# Hugging Face Spaces exposes port 7860 by default
EXPOSE 7860

# Launch FastAPI application bound to port 7860
CMD ["uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "7860"]
