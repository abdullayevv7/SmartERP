"""
Production settings for SmartERP project.
"""

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = config(  # noqa: F405
    "DJANGO_ALLOWED_HOSTS",
    default="localhost",
    cast=Csv(),  # noqa: F405
)

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CORS - strict origins in production
CORS_ALLOW_ALL_ORIGINS = False

# Database connection pooling
DATABASES["default"]["CONN_MAX_AGE"] = 600  # noqa: F405
DATABASES["default"]["OPTIONS"]["sslmode"] = "require"  # noqa: F405

# Email
EMAIL_BACKEND = config(  # noqa: F405
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")  # noqa: F405
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)  # noqa: F405
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)  # noqa: F405
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
DEFAULT_FROM_EMAIL = config(  # noqa: F405
    "DEFAULT_FROM_EMAIL", default="noreply@smarterp.com"
)

# Sentry integration
SENTRY_DSN = config("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=config("SENTRY_ENVIRONMENT", default="production"),  # noqa: F405
    )

# Logging - production level
LOGGING["root"]["level"] = "WARNING"  # noqa: F405
LOGGING["loggers"]["django"]["level"] = "WARNING"  # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "INFO"  # noqa: F405
LOGGING["loggers"]["apps"]["handlers"] = ["console", "file", "mail_admins"]  # noqa: F405

# Admin emails for error notifications
ADMINS = [
    ("Admin", config("ADMIN_EMAIL", default="admin@smarterp.com")),  # noqa: F405
]

# Celery - production optimizations
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Cache timeout - longer in production
CACHES["default"]["TIMEOUT"] = 900  # noqa: F405
