# =====================================================
# Финальная рабочая версия Dockerfile (17 ноября 2025)
# Для проекта LokomotivTicket с drf-yasg + Whitenoise + Gunicorn
# =====================================================

FROM python:3.11-slim

# Отключаем буферизацию логов и включаем переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Устанавливаем только нужные системные пакеты
# postgresql-dev → на самом деле нужен libpq-dev + gcc
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# =================================================================
# КРИТИЧЕСКИ ВАЖНО: копируем статику drf-yasg (Swagger UI / Redoc)
# Это именно то, из-за чего у тебя была пустая страница!
# =================================================================
RUN python -c "\
import shutil, os, site; \
packages_path = site.getsitepackages()[0]; \
src = os.path.join(packages_path, 'drf_yasg', 'static'); \
dst = '/app/staticfiles/drf-yasg'; \
if os.path.exists(src): \
    os.makedirs(dst, exist_ok=True); \
    shutil.copytree(src, dst, dirs_exist_ok=True); \
    print('drf-yasg static files copied to /app/staticfiles/drf-yasg'); \
else: \
    print('Warning: drf_yasg static not found at', src); \
"

# Создаём директорию для статики и собираем все статические файлы
RUN mkdir -p staticfiles
RUN python manage.py collectstatic --noinput --clear --verbosity 2

# Создаём непривилегированного пользователя
RUN adduser --disabled-password --gecos '' django && \
    chown -R django:django /app
USER django

# Запускаем Gunicorn
CMD ["gunicorn", "lokomotivTicket.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
