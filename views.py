"""
Accounts models: User, Organization, Department, Role.
Multi-tenant architecture with row-level isolation.
"""

import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Organization(models.Model):
    """
    Represents a tenant organization. All data is scoped to an organization.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    domain = models.CharField(max_length=255, blank=True, null=True, unique=True)
    logo = models.ImageField(upload_to="organizations/logos/", blank=True, null=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    timezone = models.CharField(max_length=50, default="UTC")
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            ("starter", "Starter"),
            ("professional", "Professional"),
            ("enterprise", "Enterprise"),
        ],
        default="starter",
    )
    max_users = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name

    @property
    def active_users_count(self):
        return self.users.filter(is_active=True).count()


class Department(models.Model):
    """
    Organizational department within a tenant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["organization", "code"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    @property
    def employee_count(self):
        return self.employees.filter(is_active=True).count()


class Role(models.Model):
    """
    Custom roles within an organization with granular permissions.
    """

    MODULE_CHOICES = [
        ("accounts", "Accounts"),
        ("hr", "Human Resources"),
        ("finance", "Finance"),
        ("inventory", "Inventory"),
        ("procurement", "Procurement"),
        ("sales", "Sales"),
        ("projects", "Projects"),
    ]

    PERMISSION_CHOICES = [
        ("view", "View"),
        ("create", "Create"),
        ("edit", "Edit"),
        ("delete", "Delete"),
        ("approve", "Approve"),
        ("export", "Export"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="roles"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(
        default=False, help_text="System roles cannot be deleted."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["organization", "name"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class RolePermission(models.Model):
    """
    Granular permissions assigned to a role for specific modules.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    module = models.CharField(max_length=30, choices=Role.MODULE_CHOICES)
    permission = models.CharField(max_length=20, choices=Role.PERMISSION_CHOICES)

    class Meta:
        unique_together = ["role", "module", "permission"]
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"

    def __str__(self):
        return f"{self.role.name}: {self.module}.{self.permission}"


class UserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with email-based authentication and multi-tenant support.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to="users/avatars/", blank=True, null=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    job_title = models.CharField(max_length=200, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_org_admin = models.BooleanField(
        default=False, help_text="Organization-level administrator."
    )
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["first_name", "last_name"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def has_module_permission(self, module, permission):
        """Check if user has a specific permission for a module."""
        if self.is_superuser or self.is_org_admin:
            return True
        if not self.role:
            return False
        return self.role.permissions.filter(
            module=module, permission=permission
        ).exists()

    def get_accessible_modules(self):
        """Return list of modules the user can access."""
        if self.is_superuser or self.is_org_admin:
            return [choice[0] for choice in Role.MODULE_CHOICES]
        if not self.role:
            return []
        return list(
            self.role.permissions.values_list("module", flat=True).distinct()
        )
