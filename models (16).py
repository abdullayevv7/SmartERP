"""
HR serializers for employee management, leave, attendance, and payroll.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Attendance, Employee, LeaveRequest, Payroll, Position

User = get_user_model()


class PositionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name", read_only=True
    )

    class Meta:
        model = Position
        fields = [
            "id", "title", "code", "department", "department_name",
            "description", "min_salary", "max_salary", "level",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Position.objects.create(organization=organization, **validated_data)


class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    position_title = serializers.CharField(
        source="position.title", read_only=True
    )
    department_name = serializers.CharField(
        source="user.department.name", read_only=True
    )
    years_of_service = serializers.ReadOnlyField()

    class Meta:
        model = Employee
        fields = [
            "id", "employee_id", "full_name", "email",
            "position_title", "department_name", "employment_type",
            "employment_status", "hire_date", "years_of_service",
            "is_active",
        ]


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for retrieve/create/update views."""

    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    position_title = serializers.CharField(
        source="position.title", read_only=True
    )
    manager_name = serializers.CharField(
        source="manager.user.full_name", read_only=True
    )
    years_of_service = serializers.ReadOnlyField()
    direct_reports_count = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id", "employee_id", "user", "full_name", "email",
            "position", "position_title", "manager", "manager_name",
            "employment_type", "employment_status",
            "date_of_birth", "gender", "national_id",
            "address", "city",
            "emergency_contact_name", "emergency_contact_phone",
            "hire_date", "termination_date",
            "base_salary", "annual_leave_days", "sick_leave_days",
            "remaining_annual_leave", "remaining_sick_leave",
            "bank_name", "bank_account_number", "tax_id",
            "notes", "is_active", "years_of_service",
            "direct_reports_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at",
        ]

    def get_direct_reports_count(self, obj):
        return obj.direct_reports.filter(is_active=True).count()

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Employee.objects.create(
            organization=organization, **validated_data
        )


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source="employee.user.full_name", read_only=True
    )
    approved_by_name = serializers.CharField(
        source="approved_by.full_name", read_only=True
    )

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee", "employee_name", "leave_type",
            "start_date", "end_date", "days_requested", "reason",
            "status", "approved_by", "approved_by_name",
            "approved_at", "rejection_reason", "attachment",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "approved_by", "approved_at",
            "rejection_reason", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        if attrs.get("start_date") and attrs.get("end_date"):
            if attrs["start_date"] > attrs["end_date"]:
                raise serializers.ValidationError(
                    {"end_date": "End date must be after start date."}
                )

            # Check for overlapping leave requests
            employee = attrs.get("employee")
            if employee:
                overlapping = LeaveRequest.objects.filter(
                    employee=employee,
                    status__in=["pending", "approved"],
                    start_date__lte=attrs["end_date"],
                    end_date__gte=attrs["start_date"],
                )
                if self.instance:
                    overlapping = overlapping.exclude(pk=self.instance.pk)
                if overlapping.exists():
                    raise serializers.ValidationError(
                        "There is an overlapping leave request for this period."
                    )
        return attrs

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return LeaveRequest.objects.create(
            organization=organization, **validated_data
        )


class LeaveApprovalSerializer(serializers.Serializer):
    """Serializer for approving/rejecting leave requests."""

    action = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True)


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source="employee.user.full_name", read_only=True
    )
    employee_id_display = serializers.CharField(
        source="employee.employee_id", read_only=True
    )
    hours_worked = serializers.ReadOnlyField()

    class Meta:
        model = Attendance
        fields = [
            "id", "employee", "employee_name", "employee_id_display",
            "date", "check_in", "check_out", "status",
            "overtime_hours", "hours_worked", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Attendance.objects.create(
            organization=organization, **validated_data
        )


class PayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source="employee.user.full_name", read_only=True
    )
    employee_id_display = serializers.CharField(
        source="employee.employee_id", read_only=True
    )
    approved_by_name = serializers.CharField(
        source="approved_by.full_name", read_only=True
    )

    class Meta:
        model = Payroll
        fields = [
            "id", "employee", "employee_name", "employee_id_display",
            "period_start", "period_end",
            "base_salary", "overtime_pay", "bonus", "allowances",
            "deductions", "tax", "insurance", "net_pay",
            "status", "payment_date", "payment_reference",
            "notes", "approved_by", "approved_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "net_pay", "approved_by", "created_at", "updated_at",
        ]

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Payroll.objects.create(
            organization=organization, **validated_data
        )
