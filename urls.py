"""
Tenant middleware for multi-tenant data isolation.
"""

import threading

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

_thread_locals = threading.local()


def get_current_organization():
    """Retrieve the current organization from thread-local storage."""
    return getattr(_thread_locals, "organization", None)


def get_current_user():
    """Retrieve the current user from thread-local storage."""
    return getattr(_thread_locals, "user", None)


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware that sets the current tenant (organization) based on
    the authenticated user. This allows tenant-scoped querysets
    throughout the request lifecycle.
    """

    TENANT_EXEMPT_URLS = [
        "/api/v1/accounts/login/",
        "/api/v1/accounts/register/",
        "/api/v1/accounts/token/refresh/",
        "/api/schema/",
        "/api/docs/",
        "/api/redoc/",
        "/admin/",
        "/static/",
        "/media/",
    ]

    def process_request(self, request):
        _thread_locals.user = None
        _thread_locals.organization = None

        # Skip tenant check for exempt URLs
        for exempt_url in self.TENANT_EXEMPT_URLS:
            if request.path.startswith(exempt_url):
                return None

        # Set tenant from authenticated user
        if hasattr(request, "user") and request.user.is_authenticated:
            _thread_locals.user = request.user
            _thread_locals.organization = request.user.organization

            if (
                not request.user.is_superuser
                and not request.user.organization
                and not request.path.startswith("/admin/")
            ):
                return JsonResponse(
                    {"detail": "User is not associated with any organization."},
                    status=403,
                )

        return None

    def process_response(self, request, response):
        # Clean up thread-local data after request
        _thread_locals.user = None
        _thread_locals.organization = None
        return response


class OrganizationHeaderMiddleware(MiddlewareMixin):
    """
    Optional middleware that reads the organization from a request header.
    Useful for superusers who need to switch between organizations.
    """

    ORGANIZATION_HEADER = "X-Organization-ID"

    def process_request(self, request):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return None

        org_id = request.META.get(
            f"HTTP_{self.ORGANIZATION_HEADER.replace('-', '_').upper()}"
        )
        if org_id and request.user.is_superuser:
            from .models import Organization

            try:
                organization = Organization.objects.get(id=org_id, is_active=True)
                _thread_locals.organization = organization
            except Organization.DoesNotExist:
                return JsonResponse(
                    {"detail": "Organization not found."},
                    status=404,
                )

        return None
