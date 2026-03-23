# Don't Remove Credit @VJ_Bots

FROM python:3.10-slim

# Set working directory
WORKDIR /VJ-FILTER-BOT

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies (FORCED FIX INCLUDED)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install git+https://github.com/NBBotz/IMDBKit.git

# Run bot
CMD ["python", "bot.py"]
