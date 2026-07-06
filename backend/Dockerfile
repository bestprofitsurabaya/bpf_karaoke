FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (gunakan --no-install-recommends agar lebih cepat)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy aplikasi
COPY . .

# Expose port
EXPOSE 5000

# Run dengan uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2", "--log-level", "info"]
