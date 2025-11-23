# backend/settings/dev.py
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

SECRET_KEY = 'dev-secret-key'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'lokomotiv',
        'USER': 'postgres',
        'PASSWORD': '1234',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# Добавьте для разработки
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
    '10.15.15.29',
]