FROM python:3.10-slim

WORKDIR /VJ-FILTER-BOT

COPY . .

RUN apt-get update && apt-get install -y git ffmpeg && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]
