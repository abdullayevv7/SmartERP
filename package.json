"""
Development settings for SmartERP project.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Add browsable API in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Disable throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Django Debug Toolbar (optional)
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
except ImportError:
    pass

# Celery - run tasks synchronously in dev if desired
CELERY_TASK_ALWAYS_EAGER = config(  # noqa: F405
    "CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool
)
CELERY_TASK_EAGER_PROPAGATES = True

# Simplified logging for development
LOGGING["root"]["level"] = "DEBUG"  # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405

# Disable password validators in development for convenience
AUTH_PASSWORD_VALIDATORS = []

# Cache - use local memory in development if Redis is not available
if config("USE_REDIS_CACHE", default=True, cast=bool):  # noqa: F405
    pass  # Uses Redis from base settings
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "smarterp-dev-cache",
        }
    }
