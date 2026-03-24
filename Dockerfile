FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (important)
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY . .

# Upgrade pip
RUN pip install --upgrade pip

# Install Python deps (FIXED resolver)
RUN pip install --no-cache-dir -r requirements.txt --use-deprecated=legacy-resolver

# 🔥 Install IMDbKit from GitHub (ONLY here, not in requirements)
RUN pip install --no-cache-dir git+https://github.com/NBBotz/IMDBKit.git

# Run bot
CMD ["python", "bot.py"]
