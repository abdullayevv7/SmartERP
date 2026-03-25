# =============================================================================
# SmartERP .gitignore
# =============================================================================

# Environment
.env
.env.local
.env.production
*.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg-info/
dist/
build/
eggs/
*.egg
.eggs/
*.whl
pip-wheel-metadata/
.Python
env/
venv/
.venv/
ENV/

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
/media/
/staticfiles/
/static_collected/
*.pot
*.mo

# Node / React
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnp
.pnp.js
/frontend/build/
/frontend/coverage/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.project
.classpath
.settings/
*.sublime-project
*.sublime-workspace

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
desktop.ini

# Docker
docker-compose.override.yml

# Testing
.coverage
htmlcov/
.tox/
.nox/
.pytest_cache/
coverage.xml
*.cover

# Celery
celerybeat-schedule
celerybeat.pid

# Logs
logs/
*.log

# Compiled files
*.pyc
*.pyo
*.class
*.dll
*.exe

# Secrets
*.pem
*.key
*.cert
credentials.json
service-account.json
