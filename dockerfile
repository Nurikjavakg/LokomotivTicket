FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Установить зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в образ
COPY . .

# Собираем статику для продакшена
RUN python manage.py collectstatic --noinput

# Готовим приложение
CMD ["gunicorn", "lokomotivTicket.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]