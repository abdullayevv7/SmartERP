"""
Shared permission classes for SmartERP.
"""

from rest_framework.permissions import BasePermission


class IsOrgAdmin(BasePermission):
    """Check if the user is an organization administrator."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser
            or request.user.is_org_admin
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: allow owners or organization admins.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_org_admin:
            return True

        # Check various ownership fields
        owner_fields = [
            "user", "submitted_by", "requested_by",
            "created_by", "assigned_to",
        ]
        for field in owner_fields:
            owner = getattr(obj, field, None)
            if owner and owner == request.user:
                return True

        return False


class ReadOnly(BasePermission):
    """Allow read-only access."""

    def has_permission(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS")


class IsSuperUser(BasePermission):
    """Only allow superusers."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )
