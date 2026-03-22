FROM python:3.10-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ ffmpeg git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install all other dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install IMDBKit LAST (with its dependencies)
RUN pip install --no-cache-dir git+https://github.com/NBBotz/IMDBKit

COPY . .
CMD ["python", "bot.py"]
