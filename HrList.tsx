"""
Shared mixins for SmartERP views and models.
"""

import logging

from django.db import models

from apps.accounts.middleware import get_current_organization

logger = logging.getLogger(__name__)


class TenantQuerySetMixin:
    """
    Mixin for viewsets that automatically filters querysets
    by the current user's organization (tenant).

    Usage:
        class MyViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
            ...

    The mixin expects the model to have an 'organization' field.
    Subclasses should override get_queryset() for custom logic,
    and call super().get_queryset() if they want the tenant filter applied.
    """

    tenant_field = "organization"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none()

        if user.is_superuser:
            # Superusers can optionally filter by org via header
            org = get_current_organization()
            if org:
                return queryset.filter(**{self.tenant_field: org})
            return queryset

        if user.organization:
            return queryset.filter(**{self.tenant_field: user.organization})

        return queryset.none()


class TenantModelMixin(models.Model):
    """
    Abstract model mixin that adds organization field for multi-tenancy.

    Usage:
        class MyModel(TenantModelMixin):
            ...
    """

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.organization_id:
            org = get_current_organization()
            if org:
                self.organization = org
        super().save(*args, **kwargs)


class TimestampMixin(models.Model):
    """
    Abstract model mixin adding created_at and updated_at timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """
    Abstract model mixin for soft-delete functionality.
    Records are marked as deleted but remain in the database.
    """

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class AuditMixin(models.Model):
    """
    Abstract model mixin for tracking who created/modified a record.
    """

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from apps.accounts.middleware import get_current_user

        user = get_current_user()
        if user and user.is_authenticated:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
