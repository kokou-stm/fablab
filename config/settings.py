"""
Fichier de configuration Django pour FabOS — Système Multi-tenant de Gestion de FabLab.
"""

from pathlib import Path
import os

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Chargement automatique du fichier .env si présent
env_file = BASE_DIR / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

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

# En production, activer le cache des templates compilés pour éviter la relecture disque
if DEBUG:
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
else:
    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [BASE_DIR / 'templates'],
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                    'config.context_processors.tenant_context',
                ],
                'loaders': [
                    ('django.template.loaders.cached.Loader', [
                        'django.template.loaders.filesystem.Loader',
                        'django.template.loaders.app_directories.Loader',
                    ]),
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
            conn_max_age=600,
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
                'NAME': os.environ.get('POSTGRES_DB', 'fablab_db'),
                'USER': os.environ.get('POSTGRES_USER', os.environ.get('USER', 'sekponakokou')),
                'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
                'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
                'PORT': os.environ.get('POSTGRES_PORT', '5432'),
                'ATOMIC_REQUESTS': True,
                'CONN_MAX_AGE': 600,
            }
        }
    else:
        # Si un volume persistant est monté (ex: Azure File Share en prod), la base
        # SQLite y est stockée pour survivre aux redéploiements ; sinon fichier local.
        _data_dir = os.environ.get('DJANGO_DATA_DIR')
        sqlite_path = Path(_data_dir) / 'db.sqlite3' if _data_dir else BASE_DIR / 'db.sqlite3'
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': sqlite_path,
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
        # ManifestStaticFilesStorage ajoute un hash au nom de fichier pour le cache-busting
        # et permet des headers Cache-Control: max-age=31536000 (1 an)
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
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

# ─── Cache Redis (déjà déployé via docker-compose, câblé ici) ───
REDIS_URL = os.environ.get('REDIS_URL')

if REDIS_URL and not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'TIMEOUT': 300,  # 5 minutes par défaut
            'OPTIONS': {
                'db': '1',
            },
            'KEY_PREFIX': 'fabos',
        }
    }
    # Sessions stockées en cache Redis au lieu de la base de données
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # En local / test : cache en mémoire (pas besoin de Redis)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'fabos-cache',
        }
    }
