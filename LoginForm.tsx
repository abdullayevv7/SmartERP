# =============================================================================
# SmartERP Backend Dependencies
# =============================================================================

# Django Core
Django==5.0.6
djangorestframework==3.15.1
django-cors-headers==4.3.1
django-filter==24.2

# Authentication
djangorestframework-simplejwt==5.3.1
PyJWT==2.8.0

# Database
psycopg2-binary==2.9.9
dj-database-url==2.1.0

# Redis & Caching
django-redis==5.4.0
redis==5.0.4

# Celery
celery==5.4.0
django-celery-beat==2.6.0
django-celery-results==2.5.1

# API Documentation
drf-spectacular==0.27.2

# File Handling
Pillow==10.3.0
django-storages==1.14.3

# Security
django-axes==6.4.0
django-csp==3.8

# Utilities
python-decouple==3.8
django-model-utils==4.5.0
django-import-export==3.3.8
django-auditlog==3.0.0

# Server
gunicorn==22.0.0
whitenoise==6.6.0

# Monitoring
sentry-sdk[django]==2.3.1

# Development & Testing
coverage==7.5.1
factory-boy==3.3.0
faker==25.2.0
flake8==7.0.0
black==24.4.2
isort==5.13.2
pytest-django==4.8.0
