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
        'HOST': 'localhost',
        'PORT': '5432',
    }
}