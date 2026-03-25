"""
HR Celery tasks for background processing.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, queue="hr")
def send_leave_notification(self, leave_request_id, action):
    """Send email notification when a leave request is processed."""
    try:
        from .models import LeaveRequest

        leave_request = LeaveRequest.objects.select_related(
            "employee__user", "approved_by"
        ).get(id=leave_request_id)

        employee = leave_request.employee
        subject = f"Leave Request {action.capitalize()}"

        if action == "approved":
            message = (
                f"Dear {employee.user.full_name},\n\n"
                f"Your {leave_request.get_leave_type_display()} request "
                f"from {leave_request.start_date} to {leave_request.end_date} "
                f"has been approved by {leave_request.approved_by.full_name}.\n\n"
                f"Days: {leave_request.days_requested}\n\n"
                f"Best regards,\nSmartERP HR"
            )
        else:
            message = (
                f"Dear {employee.user.full_name},\n\n"
                f"Your {leave_request.get_leave_type_display()} request "
                f"from {leave_request.start_date} to {leave_request.end_date} "
                f"has been rejected.\n\n"
                f"Reason: {leave_request.rejection_reason or 'Not specified'}\n\n"
                f"Best regards,\nSmartERP HR"
            )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employee.user.email],
            fail_silently=False,
        )
        logger.info(
            f"Leave notification sent to {employee.user.email} for request {leave_request_id}"
        )

    except Exception as exc:
        logger.error(f"Failed to send leave notification: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3, queue="hr")
def generate_payroll_for_employee(self, employee_id, period_start, period_end):
    """Generate payroll record for a single employee."""
    try:
        from .models import Attendance, Employee, Payroll

        employee = Employee.objects.get(id=employee_id)

        if isinstance(period_start, str):
            period_start = datetime.strptime(period_start, "%Y-%m-%d").date()
        if isinstance(period_end, str):
            period_end = datetime.strptime(period_end, "%Y-%m-%d").date()

        # Check if payroll already exists
        if Payroll.objects.filter(
            employee=employee,
            period_start=period_start,
            period_end=period_end,
        ).exists():
            logger.info(f"Payroll already exists for {employee.employee_id}")
            return

        # Calculate overtime from attendance
        attendance_records = Attendance.objects.filter(
            employee=employee,
            date__gte=period_start,
            date__lte=period_end,
        )
        total_overtime = attendance_records.aggregate(
            total=Sum("overtime_hours")
        )["total"] or Decimal("0")

        # Calculate overtime pay (1.5x hourly rate)
        hourly_rate = employee.base_salary / Decimal("176")  # ~22 working days * 8 hours
        overtime_pay = total_overtime * hourly_rate * Decimal("1.5")

        # Calculate tax (simplified progressive tax)
        gross = employee.base_salary + overtime_pay
        if gross <= Decimal("3000"):
            tax = gross * Decimal("0.10")
        elif gross <= Decimal("7000"):
            tax = Decimal("300") + (gross - Decimal("3000")) * Decimal("0.15")
        else:
            tax = Decimal("900") + (gross - Decimal("7000")) * Decimal("0.20")

        # Insurance (employee portion, ~5%)
        insurance = employee.base_salary * Decimal("0.05")

        payroll = Payroll.objects.create(
            organization=employee.organization,
            employee=employee,
            period_start=period_start,
            period_end=period_end,
            base_salary=employee.base_salary,
            overtime_pay=overtime_pay.quantize(Decimal("0.01")),
            tax=tax.quantize(Decimal("0.01")),
            insurance=insurance.quantize(Decimal("0.01")),
            status="calculated",
        )

        logger.info(
            f"Payroll generated for {employee.employee_id}: net_pay={payroll.net_pay}"
        )

    except Employee.DoesNotExist:
        logger.error(f"Employee {employee_id} not found")
    except Exception as exc:
        logger.error(f"Failed to generate payroll for {employee_id}: {exc}")
        raise self.retry(exc=exc, countdown=120)


@shared_task(queue="hr")
def process_daily_attendance():
    """
    End-of-day task to mark absent employees and finalize attendance.
    Runs daily at 23:55.
    """
    from .models import Attendance, Employee

    today = date.today()
    active_employees = Employee.objects.filter(
        is_active=True, employment_status="active"
    )

    created_count = 0
    for employee in active_employees:
        _, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                "organization": employee.organization,
                "status": "absent",
            },
        )
        if created:
            created_count += 1

    logger.info(
        f"Daily attendance processed: {created_count} absent records created"
    )


@shared_task(queue="hr")
def generate_monthly_payroll():
    """
    Generate payroll for all active employees at month end.
    Runs on the 28th of each month.
    """
    from .models import Employee

    today = date.today()
    period_start = today.replace(day=1)
    period_end = today

    employees = Employee.objects.filter(
        is_active=True, employment_status="active"
    )

    for employee in employees:
        generate_payroll_for_employee.delay(
            str(employee.id),
            period_start.isoformat(),
            period_end.isoformat(),
        )

    logger.info(f"Monthly payroll generation initiated for {employees.count()} employees")


@shared_task(queue="hr")
def reset_annual_leave_balances():
    """Reset annual leave balances at the start of the year."""
    from .models import Employee

    employees = Employee.objects.filter(
        is_active=True, employment_status="active"
    )
    updated = employees.update(
        remaining_annual_leave=models.F("annual_leave_days"),
        remaining_sick_leave=models.F("sick_leave_days"),
    )
    logger.info(f"Leave balances reset for {updated} employees")
