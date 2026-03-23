FROM python:3.10-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    mediainfo \
    libmediainfo0v5 \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Upgrade pip
RUN pip install --upgrade pip --root-user-action=ignore

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

# Copy project files
COPY . .

# Start bot
CMD ["python3", "bot.py"]
