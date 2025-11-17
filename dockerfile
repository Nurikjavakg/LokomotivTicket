FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# ←←← САМОЕ ГЛАВНОЕ: ПРИНУДИТЕЛЬНО копируем статику drf-yasg в staticfiles
# Это работает ВСЕГДА, независимо от структуры site-packages
RUN mkdir -p /app/staticfiles/swagger && \
    find /usr/local/lib/python3.11/site-packages -name "swagger-ui*" -o -name "favicon*" | \
    xargs -I {} cp -r {} /app/staticfiles/swagger/ 2>/dev/null || \
    find /usr/local -name "swagger-ui*" -o -name "favicon*" | \
    xargs -I {} cp -r {} /app/staticfiles/swagger/ 2>/dev/null || true

# Теперь точно собираем всю статику (включая нашу скопированную)
RUN python manage.py collectstatic --noinput --clear

# Пользователь
RUN adduser --disabled-password --gecos '' django && chown -R django:django /app
USER django

CMD ["gunicorn", "lokomotivTicket.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
