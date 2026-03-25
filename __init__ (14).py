"""
HR admin configuration.
"""

from django.contrib import admin

from .models import Attendance, Employee, LeaveRequest, Payroll, Position


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = [
        "title", "code", "department", "organization",
        "level", "min_salary", "max_salary", "is_active",
    ]
    list_filter = ["organization", "department", "level", "is_active"]
    search_fields = ["title", "code"]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "employee_id", "user", "position", "employment_type",
        "employment_status", "hire_date", "base_salary", "is_active",
    ]
    list_filter = [
        "organization", "employment_type", "employment_status", "is_active",
    ]
    search_fields = [
        "employee_id", "user__first_name", "user__last_name", "user__email",
    ]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["user", "manager"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        "employee", "leave_type", "start_date", "end_date",
        "days_requested", "status", "approved_by", "created_at",
    ]
    list_filter = ["organization", "leave_type", "status"]
    search_fields = [
        "employee__employee_id",
        "employee__user__first_name",
        "employee__user__last_name",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        "employee", "date", "check_in", "check_out",
        "status", "overtime_hours",
    ]
    list_filter = ["organization", "status", "date"]
    search_fields = ["employee__employee_id"]
    date_hierarchy = "date"


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = [
        "employee", "period_start", "period_end",
        "base_salary", "net_pay", "status", "payment_date",
    ]
    list_filter = ["organization", "status"]
    search_fields = ["employee__employee_id"]
    readonly_fields = ["net_pay", "created_at", "updated_at"]
