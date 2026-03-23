FROM python:3.10

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install git+https://github.com/NBBotz/IMDBKit.git

# Run bot
CMD ["python", "bot.py"]
