# 1-qadam: FFmpeg binar fayllarini olish (juda tez)
FROM mwader/static-ffmpeg:6.0 as ffmpeg

# 2-qadam: Asosiy Python obraz
FROM python:3.11-slim

# FFmpeg binar fayllarini ko'chirish (apt-get download/install-dan qochamiz)
COPY --from=ffmpeg /ffmpeg /usr/local/bin/
COPY --from=ffmpeg /ffprobe /usr/local/bin/

# Muhit sozlamalari
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Faqat eng zarur tizim kutubxonalari
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    nodejs \
    brotli \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kutubxonalarni o'rnatish (Keshdan foydalanish)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodni ko'chirish
COPY . .

# Papkalarni yaratish
RUN mkdir -p storage logs
