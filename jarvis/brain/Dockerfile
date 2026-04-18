FROM python:3.12-slim

# System dependencies for audio processing, SSH, and building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    openssh-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd --create-home --shell /bin/bash jarvis
WORKDIR /app

# Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Piper voice model — downloaded at build time, ~60MB
# Using Amy (medium) — clear, neutral, not creepy
RUN mkdir -p /app/voices && \
    curl -L -o /app/voices/en_US-amy-medium.onnx \
      https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx && \
    curl -L -o /app/voices/en_US-amy-medium.onnx.json \
      https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json

# Whisper model — small.en is the sweet spot for CPU
# Downloads to ~/.cache/huggingface on first run; we pre-pull it here
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='cpu', compute_type='int8')"

# App code
COPY . .
RUN chown -R jarvis:jarvis /app

USER jarvis

# Websocket port for frontend
EXPOSE 8765

CMD ["python", "-u", "server.py"]
