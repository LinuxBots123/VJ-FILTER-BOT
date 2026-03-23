FROM python:3.10

WORKDIR /app

RUN apt-get update && apt-get install -y git ffmpeg

COPY . .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 🔥 FORCE INSTALL IMDBKit (IMPORTANT)
RUN pip install git+https://github.com/NBBotz/IMDBKit.git

CMD ["python", "bot.py"]
