"""
HR models: Employee, Position, LeaveRequest, Attendance, Payroll.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.accounts.models import Organization


class Position(models.Model):
    """Job position/title within the organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="positions"
    )
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.CASCADE,
        related_name="positions",
    )
    description = models.TextField(blank=True)
    min_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    level = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(15)],
        help_text="Job level (1-15)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        unique_together = ["organization", "code"]

    def __str__(self):
        return f"{self.title} ({self.code})"


class Employee(models.Model):
    """Employee profile linked to a user account."""

    EMPLOYMENT_TYPE_CHOICES = [
        ("full_time", "Full Time"),
        ("part_time", "Part Time"),
        ("contract", "Contract"),
        ("intern", "Intern"),
        ("freelance", "Freelance"),
    ]

    EMPLOYMENT_STATUS_CHOICES = [
        ("active", "Active"),
        ("on_leave", "On Leave"),
        ("probation", "Probation"),
        ("suspended", "Suspended"),
        ("terminated", "Terminated"),
        ("resigned", "Resigned"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
        ("prefer_not_to_say", "Prefer Not to Say"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="employees"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    employee_id = models.CharField(max_length=20, unique=True)
    position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, related_name="employees"
    )
    manager = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="direct_reports",
    )
    employment_type = models.CharField(
        max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default="full_time"
    )
    employment_status = models.CharField(
        max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, default="active"
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20, choices=GENDER_CHOICES, default="prefer_not_to_say"
    )
    national_id = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    annual_leave_days = models.PositiveSmallIntegerField(default=20)
    sick_leave_days = models.PositiveSmallIntegerField(default=10)
    remaining_annual_leave = models.DecimalField(
        max_digits=5, decimal_places=1, default=20
    )
    remaining_sick_leave = models.DecimalField(
        max_digits=5, decimal_places=1, default=10
    )
    bank_name = models.CharField(max_length=200, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["employee_id"]
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    def __str__(self):
        return f"{self.employee_id} - {self.user.full_name}"

    @property
    def years_of_service(self):
        end_date = self.termination_date or timezone.now().date()
        delta = end_date - self.hire_date
        return round(delta.days / 365.25, 1)


class LeaveRequest(models.Model):
    """Employee leave requests with approval workflow."""

    LEAVE_TYPE_CHOICES = [
        ("annual", "Annual Leave"),
        ("sick", "Sick Leave"),
        ("personal", "Personal Leave"),
        ("maternity", "Maternity Leave"),
        ("paternity", "Paternity Leave"),
        ("unpaid", "Unpaid Leave"),
        ("bereavement", "Bereavement Leave"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="leave_requests"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="hr/leave_attachments/", blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.employee.user.full_name} - {self.leave_type} "
            f"({self.start_date} to {self.end_date})"
        )

    def approve(self, approved_by_user):
        """Approve the leave request and deduct from balance."""
        self.status = "approved"
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.save()

        employee = self.employee
        if self.leave_type == "annual":
            employee.remaining_annual_leave -= self.days_requested
            employee.save(update_fields=["remaining_annual_leave"])
        elif self.leave_type == "sick":
            employee.remaining_sick_leave -= self.days_requested
            employee.save(update_fields=["remaining_sick_leave"])

    def reject(self, rejected_by_user, reason=""):
        """Reject the leave request."""
        self.status = "rejected"
        self.approved_by = rejected_by_user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()


class Attendance(models.Model):
    """Daily attendance records for employees."""

    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
        ("half_day", "Half Day"),
        ("on_leave", "On Leave"),
        ("holiday", "Holiday"),
        ("work_from_home", "Work From Home"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="attendance_records"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="present"
    )
    overtime_hours = models.DecimalField(
        max_digits=4, decimal_places=1, default=0
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        unique_together = ["employee", "date"]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.date} ({self.status})"

    @property
    def hours_worked(self):
        if self.check_in and self.check_out:
            from datetime import datetime, timedelta

            check_in_dt = datetime.combine(self.date, self.check_in)
            check_out_dt = datetime.combine(self.date, self.check_out)
            if check_out_dt < check_in_dt:
                check_out_dt += timedelta(days=1)
            diff = check_out_dt - check_in_dt
            return round(diff.total_seconds() / 3600, 2)
        return 0


class Payroll(models.Model):
    """Monthly payroll records for employees."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("calculated", "Calculated"),
        ("approved", "Approved"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="payrolls"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="payrolls"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    insurance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_payrolls",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end"]
        unique_together = ["employee", "period_start", "period_end"]

    def __str__(self):
        return (
            f"{self.employee.employee_id} - "
            f"{self.period_start} to {self.period_end}"
        )

    def calculate_net_pay(self):
        """Calculate net pay from components."""
        gross = (
            self.base_salary
            + self.overtime_pay
            + self.bonus
            + self.allowances
        )
        total_deductions = self.deductions + self.tax + self.insurance
        self.net_pay = gross - total_deductions
        return self.net_pay

    def save(self, *args, **kwargs):
        if self.status in ("draft", "calculated"):
            self.calculate_net_pay()
        super().save(*args, **kwargs)
