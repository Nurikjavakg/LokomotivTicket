# backend/settings/prod.py
import os
from .base import *
from dotenv import load_dotenv
load_dotenv()  # читает .env файл (только для локального запуска)

# Отключаем дебаг в продакшене
DEBUG = True

# Разрешённые хосты
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY не задан в .env!")

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '10.15.15.29').split(',')

# База данных
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Настройки статики для продакшена
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'