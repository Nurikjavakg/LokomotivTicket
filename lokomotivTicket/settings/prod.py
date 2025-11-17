# backend/settings/prod.py
import os
from .base import *

# Если используешь Docker, dotenv можно не использовать, переменные берутся из окружения
# Но для локального теста можно оставить
from dotenv import load_dotenv
load_dotenv()  # читает .env файл (только для локального запуска)

# Отключаем дебаг в продакшене
DEBUG = False

# Разрешённые хосты
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost').split(',')

# Секретный ключ
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'fallback_local_secret_key')

# Настройки базы данных PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'lokomotiv'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),  # 'db' — имя сервиса из docker-compose
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Настройки статики для продакшена
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Если используешь collectstatic через Dockerfile
# python manage.py collectstatic --noinput