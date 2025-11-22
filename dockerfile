# Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Собираем статику
RUN python manage.py collectstatic --noinput

# Gunicorn вместо runserver
CMD ["gunicorn", "lokomotivTicket.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]