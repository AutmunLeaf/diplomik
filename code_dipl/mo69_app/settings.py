"""
Django settings for mo69_app project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production-please!')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Локальные приложения
    'acts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mo69_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mo69_app.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'diplom_db',       # Совпадает с POSTGRES_DB
        'USER': 'postgres',        # Совпадает с POSTGRES_USER
        'PASSWORD': 'postgres',    # Совпадает с тем, что в -e POSTGRES_PASSWORD
        'HOST': 'localhost',       # Так как порт проброшен на localhost
        'PORT': '5432',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (шаблоны Excel, сгенерированные файлы)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Настройки для Aspose.Cells (лицензия, если есть)
ASPOSE_LICENSE_PATH = os.getenv('ASPOSE_LICENSE_PATH', '')

# Логирование
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# === Настройки авторизации ===
LOGIN_URL = 'login'  # Использует name='login' из urls.py
LOGIN_REDIRECT_URL = 'acts:index'  # Куда перенаправлять после входа
LOGOUT_REDIRECT_URL = 'acts:index'  # Куда после выхода

MEDIA_OUTPUT_DIR = MEDIA_ROOT / 'output'
MEDIA_OUTPUT_DIR.mkdir(exist_ok=True)

# Форматы дат для форм
DATE_INPUT_FORMATS = [
    '%Y-%m-%d',      # 2024-04-26 (HTML5 standard)
    '%d.%m.%Y',      # 26.04.2024 (русский формат)
    '%d/%m/%Y',      # 26/04/2024
    '%Y/%m/%d',      # 2024/04/26
]

# Локаль
LANGUAGE_CODE = 'ru-ru'
USE_L10N = True  # Для Django < 4.0
# Для Django 4.0+: USE_L10N убран, даты форматируются через FORMAT_MODULE_PATH

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
]

CSRF_TRUSTED_ORIGINS = [
    'https://localhost:8000',
    'http://localhost:8000',
    'https://127.0.0.1:8000',
    'http://127.0.0.1:8000',
]