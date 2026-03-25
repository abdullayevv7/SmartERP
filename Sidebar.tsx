version: '3.9'

services:
  db:
    image: postgres:16-alpine
    container_name: smarterp_db
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-smarterp}
      POSTGRES_USER: ${POSTGRES_USER:-smarterp_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-smarterp_pass}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-smarterp_user} -d ${POSTGRES_DB:-smarterp}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - smarterp_network

  redis:
    image: redis:7-alpine
    container_name: smarterp_redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-smarterp_redis}
    volumes:
      - redis_data:/data
    ports:
      - "${REDIS_PORT:-6379}:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-smarterp_redis}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - smarterp_network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: smarterp_backend
    restart: unless-stopped
    command: >
      sh -c "python manage.py migrate --noinput &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2 --timeout 120"
    volumes:
      - ./backend:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings.production}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - smarterp_network

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: smarterp_celery_worker
    restart: unless-stopped
    command: celery -A config worker -l info --concurrency=4 -Q default,hr,finance,inventory
    volumes:
      - ./backend:/app
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings.production}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - smarterp_network

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: smarterp_celery_beat
    restart: unless-stopped
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ./backend:/app
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings.production}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - smarterp_network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: smarterp_frontend
    restart: unless-stopped
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - REACT_APP_API_URL=${REACT_APP_API_URL:-http://localhost/api}
    depends_on:
      - backend
    networks:
      - smarterp_network

  nginx:
    image: nginx:1.25-alpine
    container_name: smarterp_nginx
    restart: unless-stopped
    ports:
      - "${NGINX_PORT:-80}:80"
      - "${NGINX_SSL_PORT:-443}:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
    depends_on:
      - backend
      - frontend
    networks:
      - smarterp_network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  static_volume:
    driver: local
  media_volume:
    driver: local

networks:
  smarterp_network:
    driver: bridge
