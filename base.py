"""
Projects views for project management, tasks, milestones, and time tracking.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from utils.mixins import TenantQuerySetMixin

from .models import Milestone, Project, Task, TimeEntry
from .serializers import (
    MilestoneSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    TaskSerializer,
    TimeEntrySerializer,
)


class ProjectViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for projects."""

    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "projects"
    filterset_fields = ["status", "priority", "project_manager", "department", "is_billable"]
    search_fields = ["code", "name", "client_name"]
    ordering_fields = ["code", "start_date", "end_date", "progress", "budget"]

    def get_queryset(self):
        return Project.objects.filter(
            organization=self.request.user.organization
        ).select_related(
            "project_manager", "department", "created_by"
        ).prefetch_related("team_members", "milestones")

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectListSerializer
        return ProjectDetailSerializer

    @action(detail=True, methods=["get"])
    def tasks(self, request, pk=None):
        """List all tasks for a project."""
        project = self.get_object()
        tasks = project.tasks.all().select_related(
            "assigned_to", "milestone"
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            tasks = tasks.filter(status=status_filter)

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            tasks = tasks.filter(assigned_to_id=assigned_to)

        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def time_entries(self, request, pk=None):
        """List time entries for a project."""
        project = self.get_object()
        entries = project.time_entries.all().select_related(
            "user", "task"
        )
        serializer = TimeEntrySerializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        """Project statistics and metrics."""
        project = self.get_object()
        tasks = project.tasks.all()

        return Response({
            "progress": project.progress,
            "budget": {
                "total": project.budget,
                "spent": project.spent_budget,
                "remaining": project.remaining_budget,
                "utilization": project.budget_utilization,
            },
            "time": {
                "total_hours": project.total_hours,
                "billable_amount": project.total_billable_amount,
            },
            "tasks": {
                "total": tasks.count(),
                "by_status": list(
                    tasks.values("status")
                    .annotate(count=Count("id"))
                    .order_by("-count")
                ),
                "overdue": tasks.filter(
                    due_date__lt=timezone.now().date(),
                    status__in=["todo", "in_progress", "in_review"],
                ).count(),
            },
            "milestones": {
                "total": project.milestones.count(),
                "completed": project.milestones.filter(
                    status="completed"
                ).count(),
                "overdue": project.milestones.filter(
                    due_date__lt=timezone.now().date(),
                    status__in=["pending", "in_progress"],
                ).count(),
            },
            "team_size": project.team_members.count(),
        })

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Projects dashboard overview."""
        qs = self.get_queryset()
        active = qs.filter(status="active")

        return Response({
            "total_projects": qs.count(),
            "active_projects": active.count(),
            "by_status": list(
                qs.values("status")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "total_budget": active.aggregate(
                total=Sum("budget")
            )["total"] or 0,
            "total_spent": active.aggregate(
                total=Sum("spent_budget")
            )["total"] or 0,
            "average_progress": active.aggregate(
                avg=Avg("progress")
            )["avg"] or 0,
            "overdue_tasks": Task.objects.filter(
                project__organization=request.user.organization,
                due_date__lt=timezone.now().date(),
                status__in=["todo", "in_progress", "in_review"],
            ).count(),
            "my_tasks": Task.objects.filter(
                assigned_to=request.user,
                status__in=["todo", "in_progress", "in_review"],
            ).count(),
        })


class MilestoneViewSet(viewsets.ModelViewSet):
    """CRUD operations for project milestones."""

    serializer_class = MilestoneSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "projects"
    filterset_fields = ["project", "status"]
    ordering_fields = ["order", "due_date"]

    def get_queryset(self):
        return Milestone.objects.filter(
            project__organization=self.request.user.organization
        ).select_related("project")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark a milestone as completed."""
        milestone = self.get_object()
        milestone.status = "completed"
        milestone.completed_date = timezone.now().date()
        milestone.save()
        return Response(MilestoneSerializer(milestone).data)


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD operations for project tasks."""

    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "projects"
    filterset_fields = [
        "project", "milestone", "status", "priority",
        "assigned_to",
    ]
    search_fields = ["title", "description"]
    ordering_fields = ["order", "priority", "due_date", "created_at"]

    def get_queryset(self):
        return Task.objects.filter(
            project__organization=self.request.user.organization
        ).select_related(
            "project", "assigned_to", "milestone", "created_by"
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark task as completed."""
        task = self.get_object()
        task.complete()
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["post"])
    def change_status(self, request, pk=None):
        """Change task status."""
        task = self.get_object()
        new_status = request.data.get("status")

        valid_statuses = [s[0] for s in Task.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {"detail": f"Invalid status. Choose from: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task.status = new_status
        if new_status == "completed":
            task.completed_date = timezone.now()
        task.save()
        task.project.calculate_progress()

        return Response(TaskSerializer(task).data)

    @action(detail=False, methods=["get"])
    def my_tasks(self, request):
        """Get tasks assigned to the current user."""
        tasks = self.get_queryset().filter(
            assigned_to=request.user
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            tasks = tasks.filter(status=status_filter)

        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def board(self, request):
        """Get tasks organized by status (Kanban board view)."""
        project_id = request.query_params.get("project")
        if not project_id:
            return Response(
                {"detail": "project query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tasks = self.get_queryset().filter(project_id=project_id)
        board = {}
        for status_choice in Task.STATUS_CHOICES:
            status_key = status_choice[0]
            status_tasks = tasks.filter(status=status_key)
            board[status_key] = TaskSerializer(status_tasks, many=True).data

        return Response(board)


class TimeEntryViewSet(viewsets.ModelViewSet):
    """CRUD operations for time entries."""

    serializer_class = TimeEntrySerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "projects"
    filterset_fields = [
        "project", "task", "user", "date", "is_billable", "is_approved",
    ]
    search_fields = ["description"]
    ordering_fields = ["date", "hours", "billable_amount"]

    def get_queryset(self):
        qs = TimeEntry.objects.filter(
            project__organization=self.request.user.organization
        ).select_related("project", "task", "user", "approved_by")

        # Non-admin users see only their own entries
        user = self.request.user
        if not user.is_org_admin and not user.is_superuser:
            if not user.has_module_permission("projects", "approve"):
                qs = qs.filter(user=user)

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a time entry."""
        entry = self.get_object()
        entry.is_approved = True
        entry.approved_by = request.user
        entry.save()
        return Response(TimeEntrySerializer(entry).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Time entry summary for a given period."""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        qs = self.get_queryset()
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        return Response({
            "total_hours": qs.aggregate(total=Sum("hours"))["total"] or 0,
            "billable_hours": qs.filter(is_billable=True).aggregate(
                total=Sum("hours")
            )["total"] or 0,
            "total_billable_amount": qs.filter(is_billable=True).aggregate(
                total=Sum("billable_amount")
            )["total"] or 0,
            "by_project": list(
                qs.values("project__code", "project__name")
                .annotate(
                    total_hours=Sum("hours"),
                    total_billable=Sum("billable_amount"),
                )
                .order_by("-total_hours")
            ),
            "by_user": list(
                qs.values("user__first_name", "user__last_name")
                .annotate(total_hours=Sum("hours"))
                .order_by("-total_hours")
            ),
        })
