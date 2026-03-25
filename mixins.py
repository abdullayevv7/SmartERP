"""
Celery configuration for SmartERP project.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("smarterp")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Periodic tasks schedule
app.conf.beat_schedule = {
    "process-daily-attendance": {
        "task": "apps.hr.tasks.process_daily_attendance",
        "schedule": crontab(hour=23, minute=55),
        "options": {"queue": "hr"},
    },
    "generate-monthly-payroll": {
        "task": "apps.hr.tasks.generate_monthly_payroll",
        "schedule": crontab(day_of_month=28, hour=2, minute=0),
        "options": {"queue": "hr"},
    },
    "check-low-stock-alerts": {
        "task": "apps.inventory.tasks.check_low_stock",
        "schedule": crontab(hour="*/4", minute=0),
        "options": {"queue": "inventory"},
    },
    "generate-daily-financial-summary": {
        "task": "apps.finance.tasks.generate_daily_summary",
        "schedule": crontab(hour=1, minute=0),
        "options": {"queue": "finance"},
    },
    "cleanup-expired-tokens": {
        "task": "apps.accounts.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=3, minute=0),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery connectivity."""
    print(f"Request: {self.request!r}")
