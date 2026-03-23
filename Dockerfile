# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r /requirements.txt

# Create working directory
WORKDIR /VJ-FILTER-BOT

# Copy project files
COPY . .

# Run bot
CMD ["python", "bot.py"]
