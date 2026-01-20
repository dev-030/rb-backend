from pathlib import Path
import environ

from datetime import timedelta


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent




env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')



SECRET_KEY = 'django-insecure-f$hk^nfn)q)9!di(p&!f6j-$)2#h*z+_ks&fsdf3t)bv@i4*e5'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


ALLOWED_HOSTS = ["*"]


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# In build apps
INSTALLED_APPS += [
    "authentication",
    "users",
    "agency",
    "employer", 
    "trainer",
    "adminpanel"
]

# Third party apps
INSTALLED_APPS += [
    'rest_framework',
    'corsheaders',
    'cloudinary',
    'cloudinary_storage',
    'rest_framework_simplejwt'
]


AUTH_USER_MODEL = "authentication.UserAccount"

# Authentication backends - required for email-based login
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]



MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Email configuration - SMTP for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='neworkx@platform.com')
OTP_VALIDITY_DURATION = 5  # minutes



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'rbwoodroff',       
        'USER': 'jamil',     
        'PASSWORD': '',    
        'HOST': 'localhost',         
        'PORT': '5432',              
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = False  # Must be False when credentials are allowed
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.0.111:3000",
    "https://api.neworkx.com",
    "https://dashboard.neworkx.com"
]

# Explicitly allow all HTTP methods including PATCH
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Allow all common headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    'https://api.neworkx.com',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://192.168.0.111:3000',
    'https://dashboard.neworkx.com',
]



# Cloudinary setup - For production, use env variables
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUD_NAME', default='demo'),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default='')
}

import cloudinary
cloudinary.config(
    cloud_name = CLOUDINARY_STORAGE['CLOUD_NAME'], 
    api_key = CLOUDINARY_STORAGE['API_KEY'], 
    api_secret = CLOUDINARY_STORAGE['API_SECRET']
)   

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Stripe setup - Using test mode for development
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="sk_test_")
STRIPE_PUBLIC_KEY = env("STRIPE_PUBLIC_KEY", default="pk_test_")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
DOMAIN_URL = env("DOMAIN_URL", default="http://localhost:8000")
REGISTRATION_FEE = 150.00  # USD

# Stripe Checkout redirect URLs (customize in .env for production)
STRIPE_SUCCESS_URL = env("STRIPE_SUCCESS_URL")
STRIPE_CANCEL_URL = env("STRIPE_CANCEL_URL")

# # google login
# GOOGLE_CLIENT_ID = env('GOOGLE_CLIENT_ID')
# GOOGLE_CLIENT_SECRET = env('GOOGLE_CLIENT_SECRET')
# GOOGLE_REDIRECT_URI = env('GOOGLE_REDIRECT_URI')



SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=17),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'SIGNING_KEY': env('SIGNING_KEY'),
}

# OpenAI configuration for AI career analysis
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
OPENAI_MODEL = env('OPENAI_MODEL', default='gpt-4o')  # GPT-4o: cheaper + vision support
# Env updated - reload trigger