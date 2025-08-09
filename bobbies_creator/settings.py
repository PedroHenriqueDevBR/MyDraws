import os
from pathlib import Path

from decouple import Csv, config
import stripe

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", cast=bool, default=True)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=Csv())


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party apps
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # Custom apps
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "bobbies_creator.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Custom context processors
                "core.services.context_processors.user_credit_amount",
            ],
        },
    },
]

AUTH_USER_MODEL = "core.Profile"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Payment settings
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET")

stripe.api_key = STRIPE_SECRET_KEY

CREDIT_PACKAGES = [
    {
        "id": "pack_50",
        "amount": 999,
        "credits": 50,
        "label": "50 Credits",
    },
    {
        "id": "pack_90",
        "amount": 1499,
        "credits": 90,
        "label": "90 Credits (15 for free)",
    },
    {
        "id": "pack_150",
        "amount": 2499,
        "credits": 150,
        "label": "150 Credits (25 for free)",
    },
]


# Auth settings

SITE_ID = 2
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_LOGIN_METHODS = {"email"}

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "OAUTH_PKCE_ENABLED": True,
        "FETCH_USERINFO": True,
    },
}

WSGI_APPLICATION = "bobbies_creator.wsgi.application"
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/mydraws/"

DEVELOPMENT_DB = config("DEVELOPMENT_DB", default=False, cast=bool)

if DEVELOPMENT_DB:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="postgres"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default="postgres"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }


V1 = "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
V2 = "django.contrib.auth.password_validation.MinimumLengthValidator"
V3 = "django.contrib.auth.password_validation.CommonPasswordValidator"
V4 = "django.contrib.auth.password_validation.NumericPasswordValidator"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": V1},
    {"NAME": V2},
    {"NAME": V3},
    {"NAME": V4},
]

# Internationalization
LANGUAGE_CODE = "en"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("pt-br", "Português (Brasil)"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles/"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "mediafiles/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
