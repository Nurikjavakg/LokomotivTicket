FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Установить системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-dev \
    && rm -rf /var/lib/apt/lists/*

# Установить зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в образ
COPY . .

# Создаем директории для статики
RUN mkdir -p staticfiles static

RUN cp -r /usr/local/lib/python3.11/site-packages/drf_yasg/static/* /app/staticfiles/ || true

# Собираем статику для продакшена
RUN python manage.py collectstatic --noinput

# Создаем пользователя для безопасности
RUN useradd -m -r django && chown -R django /app
USER django

EXPOSE 8000

CMD ["gunicorn", "lokomotivTicket.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
