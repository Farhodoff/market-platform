FROM python:3.11-slim

WORKDIR /app

# Muhit o'zgaruvchilari
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Tizim paketlari
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Bog'liqliklarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini nusxalash
COPY . .

# Papkalarni yaratish
RUN mkdir -p uploads static/products

EXPOSE 3000

# Gunicorn WSGI serveri orqali ishga tushirish
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "3", "--timeout", "60", "server:app"]
