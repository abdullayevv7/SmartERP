"""
Project Management models: Project, Task, Milestone, TimeEntry.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import Organization


class Project(models.Model):
    """Project management with budgets, timelines, and team assignments."""

    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("active", "Active"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("archived", "Archived"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="projects"
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="planning"
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="managed_projects",
    )
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_projects",
    )
    client_name = models.CharField(max_length=300, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    spent_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    hourly_rate = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Default billable rate per hour",
    )
    is_billable = models.BooleanField(default=True)
    progress = models.PositiveSmallIntegerField(
        default=0, help_text="Overall progress percentage (0-100)"
    )
    tags = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated tags",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["organization", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def remaining_budget(self):
        return self.budget - self.spent_budget

    @property
    def budget_utilization(self):
        if self.budget <= 0:
            return 0
        return round(float(self.spent_budget / self.budget * 100), 1)

    @property
    def total_hours(self):
        return (
            self.time_entries.aggregate(total=models.Sum("hours"))["total"]
            or Decimal("0")
        )

    @property
    def total_billable_amount(self):
        return (
            self.time_entries.filter(is_billable=True).aggregate(
                total=models.Sum("billable_amount")
            )["total"]
            or Decimal("0")
        )

    def calculate_progress(self):
        """Calculate progress based on completed tasks."""
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        completed = self.tasks.filter(status="completed").count()
        self.progress = round(completed / total_tasks * 100)
        self.save(update_fields=["progress"])
        return self.progress


class Milestone(models.Model):
    """Project milestone for tracking key deliverables."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("overdue", "Overdue"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="milestones"
    )
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "due_date"]

    def __str__(self):
        return f"{self.project.code}: {self.name}"

    @property
    def is_overdue(self):
        if self.status == "completed":
            return False
        return timezone.now().date() > self.due_date

    @property
    def tasks_count(self):
        return self.tasks.count()

    @property
    def completed_tasks_count(self):
        return self.tasks.filter(status="completed").count()


class Task(models.Model):
    """Individual tasks within a project."""

    STATUS_CHOICES = [
        ("backlog", "Backlog"),
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("in_review", "In Review"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="tasks"
    )
    milestone = models.ForeignKey(
        Milestone, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tasks",
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subtasks",
    )
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="todo"
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    estimated_hours = models.DecimalField(
        max_digits=6, decimal_places=1, default=0
    )
    actual_hours = models.DecimalField(
        max_digits=6, decimal_places=1, default=0
    )
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    tags = models.CharField(max_length=300, blank=True)
    attachment = models.FileField(
        upload_to="projects/tasks/", blank=True, null=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-priority", "due_date"]

    def __str__(self):
        return f"{self.project.code}: {self.title}"

    @property
    def is_overdue(self):
        if self.status == "completed" or not self.due_date:
            return False
        return timezone.now().date() > self.due_date

    def complete(self):
        """Mark task as completed."""
        self.status = "completed"
        self.completed_date = timezone.now()
        self.save()
        self.project.calculate_progress()


class TimeEntry(models.Model):
    """Time tracking entries for project tasks."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="time_entries"
    )
    task = models.ForeignKey(
        Task, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="time_entries",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField()
    is_billable = models.BooleanField(default=True)
    hourly_rate = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    billable_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_time_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Time Entries"

    def __str__(self):
        return (
            f"{self.user.full_name} - {self.project.code}: "
            f"{self.hours}h on {self.date}"
        )

    def save(self, *args, **kwargs):
        if not self.hourly_rate and self.project:
            self.hourly_rate = self.project.hourly_rate
        if self.is_billable:
            self.billable_amount = self.hours * self.hourly_rate
        else:
            self.billable_amount = Decimal("0")
        super().save(*args, **kwargs)
