"""
Accounts permissions for module-level access control.
"""

from rest_framework.permissions import BasePermission


class HasModulePermission(BasePermission):
    """
    Check if the user has the required permission for the module.
    The view must define `module_name` attribute.
    Maps HTTP methods to permission types.
    """

    METHOD_PERMISSION_MAP = {
        "GET": "view",
        "HEAD": "view",
        "OPTIONS": "view",
        "POST": "create",
        "PUT": "edit",
        "PATCH": "edit",
        "DELETE": "delete",
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_org_admin:
            return True

        module_name = getattr(view, "module_name", None)
        if not module_name:
            return False

        permission_type = self.METHOD_PERMISSION_MAP.get(request.method, "view")
        return request.user.has_module_permission(module_name, permission_type)


class HasApprovalPermission(BasePermission):
    """
    Check if the user has approval permission for the module.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_org_admin:
            return True

        module_name = getattr(view, "module_name", None)
        if not module_name:
            return False

        return request.user.has_module_permission(module_name, "approve")


class IsOrganizationMember(BasePermission):
    """
    Ensure the user belongs to the same organization as the requested resource.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        obj_org = getattr(obj, "organization", None)
        if obj_org is None:
            obj_org = getattr(obj, "organization_id", None)

        return obj_org == request.user.organization or obj_org == request.user.organization_id


class CanExportData(BasePermission):
    """
    Check if user has export permission for the module.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_org_admin:
            return True

        module_name = getattr(view, "module_name", None)
        if not module_name:
            return False

        return request.user.has_module_permission(module_name, "export")
