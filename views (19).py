"""
HR views for employee management, leave requests, attendance, and payroll.
"""

from datetime import date, timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasApprovalPermission, HasModulePermission
from utils.mixins import TenantQuerySetMixin

from .models import Attendance, Employee, LeaveRequest, Payroll, Position
from .serializers import (
    AttendanceSerializer,
    EmployeeDetailSerializer,
    EmployeeListSerializer,
    LeaveApprovalSerializer,
    LeaveRequestSerializer,
    PayrollSerializer,
    PositionSerializer,
)
from .tasks import generate_payroll_for_employee, send_leave_notification


class PositionViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for job positions."""

    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "hr"
    filterset_fields = ["department", "is_active", "level"]
    search_fields = ["title", "code"]
    ordering_fields = ["title", "level"]

    def get_queryset(self):
        return Position.objects.filter(
            organization=self.request.user.organization
        ).select_related("department")


class EmployeeViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for employees with analytics."""

    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "hr"
    filterset_fields = [
        "employment_type", "employment_status", "is_active",
        "position", "user__department",
    ]
    search_fields = [
        "employee_id", "user__first_name", "user__last_name",
        "user__email",
    ]
    ordering_fields = ["employee_id", "hire_date", "base_salary"]

    def get_queryset(self):
        return Employee.objects.filter(
            organization=self.request.user.organization
        ).select_related("user", "position", "manager__user", "user__department")

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeeListSerializer
        return EmployeeDetailSerializer

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Return HR statistics for the dashboard."""
        qs = self.get_queryset()
        active = qs.filter(is_active=True)

        stats = {
            "total_employees": active.count(),
            "by_employment_type": list(
                active.values("employment_type")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "by_status": list(
                active.values("employment_status")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "by_department": list(
                active.values("user__department__name")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "average_salary": active.aggregate(avg=Avg("base_salary"))["avg"],
            "new_hires_this_month": active.filter(
                hire_date__month=timezone.now().month,
                hire_date__year=timezone.now().year,
            ).count(),
            "pending_leave_requests": LeaveRequest.objects.filter(
                organization=request.user.organization,
                status="pending",
            ).count(),
        }
        return Response(stats)

    @action(detail=True, methods=["get"])
    def direct_reports(self, request, pk=None):
        """List direct reports for the specified employee."""
        employee = self.get_object()
        reports = employee.direct_reports.filter(is_active=True)
        serializer = EmployeeListSerializer(reports, many=True)
        return Response(serializer.data)


class LeaveRequestViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for leave requests with approval workflow."""

    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "hr"
    filterset_fields = ["employee", "leave_type", "status"]
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    ordering_fields = ["start_date", "created_at", "status"]

    def get_queryset(self):
        qs = LeaveRequest.objects.filter(
            organization=self.request.user.organization
        ).select_related("employee__user", "approved_by")

        # Non-admin users see only their own or their direct reports' requests
        user = self.request.user
        if not user.is_org_admin and not user.is_superuser:
            employee = getattr(user, "employee_profile", None)
            if employee:
                report_ids = employee.direct_reports.values_list("id", flat=True)
                qs = qs.filter(
                    Q(employee=employee) | Q(employee_id__in=report_ids)
                )
            else:
                qs = qs.none()

        return qs

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        """Approve or reject a leave request."""
        leave_request = self.get_object()

        if leave_request.status != "pending":
            return Response(
                {"detail": "Only pending requests can be processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeaveApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_type = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")

        if action_type == "approve":
            leave_request.approve(request.user)
            send_leave_notification.delay(
                str(leave_request.id), "approved"
            )
        else:
            leave_request.reject(request.user, reason)
            send_leave_notification.delay(
                str(leave_request.id), "rejected"
            )

        return Response(
            LeaveRequestSerializer(leave_request).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def calendar(self, request):
        """Return leave data formatted for calendar display."""
        month = int(request.query_params.get("month", timezone.now().month))
        year = int(request.query_params.get("year", timezone.now().year))

        leaves = self.get_queryset().filter(
            status="approved",
            start_date__year=year,
            start_date__month=month,
        ).values(
            "id", "employee__user__first_name", "employee__user__last_name",
            "leave_type", "start_date", "end_date",
        )

        return Response(list(leaves))


class AttendanceViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for attendance records."""

    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "hr"
    filterset_fields = ["employee", "date", "status"]
    search_fields = [
        "employee__employee_id",
        "employee__user__first_name",
        "employee__user__last_name",
    ]
    ordering_fields = ["date", "check_in"]

    def get_queryset(self):
        return Attendance.objects.filter(
            organization=self.request.user.organization
        ).select_related("employee__user")

    @action(detail=False, methods=["post"])
    def check_in(self, request):
        """Clock in for the current user."""
        employee = getattr(request.user, "employee_profile", None)
        if not employee:
            return Response(
                {"detail": "No employee profile found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()
        attendance, created = Attendance.objects.get_or_create(
            organization=request.user.organization,
            employee=employee,
            date=today,
            defaults={
                "check_in": timezone.now().time(),
                "status": "present",
            },
        )

        if not created:
            if attendance.check_in:
                return Response(
                    {"detail": "Already checked in today."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            attendance.check_in = timezone.now().time()
            attendance.status = "present"
            attendance.save()

        return Response(AttendanceSerializer(attendance).data)

    @action(detail=False, methods=["post"])
    def check_out(self, request):
        """Clock out for the current user."""
        employee = getattr(request.user, "employee_profile", None)
        if not employee:
            return Response(
                {"detail": "No employee profile found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()
        try:
            attendance = Attendance.objects.get(
                employee=employee, date=today
            )
        except Attendance.DoesNotExist:
            return Response(
                {"detail": "No check-in record found for today."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attendance.check_out = timezone.now().time()
        attendance.save()
        return Response(AttendanceSerializer(attendance).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Return attendance summary for the current month."""
        today = timezone.now().date()
        month_start = today.replace(day=1)

        qs = self.get_queryset().filter(
            date__gte=month_start, date__lte=today
        )

        summary = {
            "total_records": qs.count(),
            "by_status": list(
                qs.values("status")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "average_overtime": qs.aggregate(
                avg=Avg("overtime_hours")
            )["avg"] or 0,
            "total_overtime": qs.aggregate(
                total=Sum("overtime_hours")
            )["total"] or 0,
        }
        return Response(summary)


class PayrollViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for payroll processing."""

    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "hr"
    filterset_fields = ["employee", "status", "period_start", "period_end"]
    search_fields = [
        "employee__employee_id",
        "employee__user__first_name",
        "employee__user__last_name",
    ]
    ordering_fields = ["period_end", "net_pay"]

    def get_queryset(self):
        return Payroll.objects.filter(
            organization=self.request.user.organization
        ).select_related("employee__user", "approved_by")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a payroll record."""
        payroll = self.get_object()
        if payroll.status not in ("draft", "calculated"):
            return Response(
                {"detail": "Only draft or calculated payrolls can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payroll.status = "approved"
        payroll.approved_by = request.user
        payroll.save()
        return Response(PayrollSerializer(payroll).data)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        """Mark a payroll record as paid."""
        payroll = self.get_object()
        if payroll.status != "approved":
            return Response(
                {"detail": "Only approved payrolls can be marked as paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payroll.status = "paid"
        payroll.payment_date = timezone.now().date()
        payroll.payment_reference = request.data.get("payment_reference", "")
        payroll.save()
        return Response(PayrollSerializer(payroll).data)

    @action(detail=False, methods=["post"])
    def generate_batch(self, request):
        """Generate payroll for all active employees for a given period."""
        period_start = request.data.get("period_start")
        period_end = request.data.get("period_end")

        if not period_start or not period_end:
            return Response(
                {"detail": "period_start and period_end are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employees = Employee.objects.filter(
            organization=request.user.organization,
            is_active=True,
            employment_status="active",
        )

        created_count = 0
        for employee in employees:
            exists = Payroll.objects.filter(
                employee=employee,
                period_start=period_start,
                period_end=period_end,
            ).exists()
            if not exists:
                generate_payroll_for_employee.delay(
                    str(employee.id), period_start, period_end
                )
                created_count += 1

        return Response(
            {"detail": f"Payroll generation initiated for {created_count} employees."},
            status=status.HTTP_202_ACCEPTED,
        )
