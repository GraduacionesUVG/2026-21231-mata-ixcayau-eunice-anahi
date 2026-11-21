from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY', default='inseguro-cambia-esto-en-produccion')
DEBUG = env.bool('DJANGO_DEBUG', default=True)
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env.list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])

# nginx termina el HTTPS y le habla a gunicorn por HTTP interno - sin esto,
# Django no sabe que la conexión original del navegador fue HTTPS (rompe
# CSRF y cualquier cookie marcada como "Secure").
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# con DEBUG=False, Django por default manda los errores 500 por correo a
# ADMINS en vez de la consola - sin esto, "docker compose logs" no muestra
# nada cuando algo truena en producción.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'sucursales',
    'productos',
    'proveedores',
    'inventario',
    'usuarios',
    'ventas',
    'clientes',
    'reportes',
    'pedidos',
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
                'core.context_processors.nav',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Postgres propio (servicio "db" de docker-compose), conexión directa vía
# psycopg. Sin RLS: los filtros de acceso por rol/sucursal van a mano en
# cada queryset.
DATABASES = {
    'default': env.db('DATABASE_URL'),
}
# CONN_MAX_AGE reutiliza la conexión entre requests en vez de abrir una
# nueva en cada navegación. Con Postgres local el costo de una conexión
# nueva es bajo, pero igual se evita reabrir en cada request; 60s además
# limita cuánto puede durar "colgada" una conexión si el contenedor se
# reinicia a medio request (--force-recreate al tocar .env).
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Guatemala'  # ajusta a tu zona horaria real
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Logos de empresa e imágenes de producto (antes en Supabase Storage,
# ahora una carpeta local - ver core/storage.py).
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Etiqueta de producto (código de barras ZPL) ---
# Todo lo que es tamaño/posición va en milímetros; productos/zpl.py lo
# convierte a puntos según el DPI. Para cambiar de impresora o de sticker
# en el futuro, solo hay que tocar esto y productos/templates/productos/etiqueta.zpl
# - el resto del código no sabe nada de ZPL ni de impresoras.
ETIQUETA_ZPL = {
    'DPI': 203,  # Zebra ZD420, 203 dpi
    'ANCHO_MM': 51,
    'ALTO_MM': 31,
    'MARGEN_IZQ_MM': 3,
    'NOMBRE_Y_MM': 2,
    'NOMBRE_ALTO_MM': 3.2,
    'NOMBRE_MAX_CARACTERES': 24,
    'BARCODE_Y_MM': 7,
    'BARCODE_ALTO_MM': 14,
    'BARCODE_MODULO_MM': 0.25,  # ancho de la barra angosta
    'BARCODE_RATIO': 3,  # relación barra ancha/angosta
}

LOGIN_URL = 'core:login'

# 'error' -> 'danger' para que el CSS de alertas lo reconozca.
from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}
