"""
Accounts admin configuration.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Department, Organization, Role, RolePermission, User


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        "name", "slug", "subscription_plan", "max_users",
        "active_users_count", "is_active", "created_at",
    ]
    list_filter = ["subscription_plan", "is_active", "country"]
    search_fields = ["name", "slug", "email", "domain"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email", "full_name", "organization", "department",
        "role", "is_active", "is_org_admin", "date_joined",
    ]
    list_filter = [
        "is_active", "is_staff", "is_superuser",
        "is_org_admin", "organization",
    ]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "phone", "avatar")}),
        (
            "Organization",
            {"fields": ("organization", "department", "role", "job_title")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active", "is_staff", "is_superuser",
                    "is_org_admin", "groups", "user_permissions",
                ),
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined", "password_changed_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email", "first_name", "last_name",
                    "password1", "password2", "organization",
                ),
            },
        ),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = [
        "name", "code", "organization", "head",
        "parent", "is_active",
    ]
    list_filter = ["organization", "is_active"]
    search_fields = ["name", "code"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "is_system_role", "created_at"]
    list_filter = ["organization", "is_system_role"]
    search_fields = ["name"]
    inlines = [RolePermissionInline]
    readonly_fields = ["created_at", "updated_at"]
