"""
Fichier de configuration Django pour FabOS — Système Multi-tenant de Gestion de FabLab.
"""

from pathlib import Path
import os

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-fabos-multitenant-fablab-key-super-secret-local-dev')

DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# Le conteneur ACI ne fait que du HTTP ; quand il est servi derrière un proxy TLS
# (ex: Cloudflare en mode Flexible), celui-ci indique le vrai protocole via cet en-tête.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'django_htmx',

    # Core App
    'core',

    # Master Apps
    'fablabs',
    'accounts',

    # Tenant Apps
    'equipment',
    'reservations',
    'workshops',
    'inventory',
    'projects',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',

    # Custom Multi-tenant Middleware
    'config.tenant_middleware.TenantMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
                'config.context_processors.tenant_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Configuration Multi-tenant Database Router
DATABASE_ROUTERS = ['config.tenant_router.TenantRouter']

# Configuration Base de Données :
# Mode Local (Postgres local / SQLite local) activé par défaut pour le déploiement courant.
# Pour basculer sur la base Postgres Cloud Prod plus tard : définir USE_PROD_POSTGRES=1 et DATABASE_URL
USE_PROD_POSTGRES = os.environ.get('USE_PROD_POSTGRES', '0') == '1'
DATABASE_URL = os.environ.get('DATABASE_URL')

if USE_PROD_POSTGRES and DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=60,
            ssl_require=True,
        )
    }
    DATABASES['default']['ATOMIC_REQUESTS'] = True
else:
    USE_POSTGRES = os.environ.get('USE_POSTGRES', '1') == '1'
    if USE_POSTGRES:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'fablab_db',
                'USER': os.environ.get('POSTGRES_USER', os.environ.get('USER', 'sekponakokou')),
                'PASSWORD': '',
                'HOST': 'localhost',
                'PORT': '5432',
                'ATOMIC_REQUESTS': True,
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
                'ATOMIC_REQUESTS': True,
            }
        }

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# En local (DEBUG=True), sert directement depuis STATICFILES_DIRS sans nécessiter collectstatic
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG

MEDIA_URL = '/media/'
DJANGO_DATA_DIR = os.environ.get('DJANGO_DATA_DIR')
MEDIA_ROOT = Path(DJANGO_DATA_DIR) / 'media' if DJANGO_DATA_DIR else BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuration Envoi d'Emails (Gmail SMTP avec les identifiants du projet app_save)
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'voicetranslator0@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'LabOS Platform <voicetranslator0@gmail.com>')
