FROM python:3.11-slim
WORKDIR /app

# FFmpeg diperlukan untuk pitch/key shift & pipeline media
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "5000"]
