# backend/settings/prod.py
import os
from .base import *
from dotenv import load_dotenv
load_dotenv()  # читает .env файл (только для локального запуска)

# Отключаем дебаг в продакшене
DEBUG = False

# Разрешённые хосты
ALLOWED_HOSTS = ['10.15.15.29', 'localhost', '127.0.0.1', '[::1]', 'web', 'web:8000']

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
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
