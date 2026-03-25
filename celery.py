"""
Projects serializers.
"""

from rest_framework import serializers

from .models import Milestone, Project, Task, TimeEntry


class TimeEntrySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    project_name = serializers.CharField(
        source="project.name", read_only=True
    )
    task_title = serializers.CharField(
        source="task.title", read_only=True
    )
    approved_by_name = serializers.CharField(
        source="approved_by.full_name", read_only=True
    )

    class Meta:
        model = TimeEntry
        fields = [
            "id", "project", "project_name",
            "task", "task_title",
            "user", "user_name", "date",
            "hours", "description", "is_billable",
            "hourly_rate", "billable_amount",
            "is_approved", "approved_by", "approved_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "billable_amount", "approved_by",
            "created_at", "updated_at",
        ]


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True
    )
    project_code = serializers.CharField(
        source="project.code", read_only=True
    )
    milestone_name = serializers.CharField(
        source="milestone.name", read_only=True
    )
    is_overdue = serializers.ReadOnlyField()
    subtasks_count = serializers.SerializerMethodField()
    time_logged = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "project", "project_code",
            "milestone", "milestone_name",
            "parent", "title", "description",
            "status", "priority",
            "assigned_to", "assigned_to_name",
            "estimated_hours", "actual_hours",
            "start_date", "due_date", "completed_date",
            "order", "tags", "attachment",
            "is_overdue", "subtasks_count", "time_logged",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "completed_date", "created_by",
            "created_at", "updated_at",
        ]

    def get_subtasks_count(self, obj):
        return obj.subtasks.count()

    def get_time_logged(self, obj):
        from django.db.models import Sum
        return obj.time_entries.aggregate(
            total=Sum("hours")
        )["total"] or 0


class MilestoneSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    tasks_count = serializers.ReadOnlyField()
    completed_tasks_count = serializers.ReadOnlyField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Milestone
        fields = [
            "id", "project", "name", "description",
            "status", "due_date", "completed_date", "order",
            "is_overdue", "tasks_count", "completed_tasks_count",
            "progress", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_progress(self, obj):
        total = obj.tasks_count
        if total == 0:
            return 0
        return round(obj.completed_tasks_count / total * 100)


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight project serializer for list views."""

    project_manager_name = serializers.CharField(
        source="project_manager.full_name", read_only=True
    )
    department_name = serializers.CharField(
        source="department.name", read_only=True
    )
    total_hours = serializers.ReadOnlyField()
    remaining_budget = serializers.ReadOnlyField()
    budget_utilization = serializers.ReadOnlyField()
    tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "code", "name", "status", "priority",
            "project_manager", "project_manager_name",
            "department", "department_name",
            "client_name", "start_date", "end_date",
            "budget", "spent_budget", "remaining_budget",
            "budget_utilization", "progress",
            "total_hours", "is_billable", "tasks_count",
        ]

    def get_tasks_count(self, obj):
        return obj.tasks.count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Detailed project serializer."""

    project_manager_name = serializers.CharField(
        source="project_manager.full_name", read_only=True
    )
    department_name = serializers.CharField(
        source="department.name", read_only=True
    )
    total_hours = serializers.ReadOnlyField()
    total_billable_amount = serializers.ReadOnlyField()
    remaining_budget = serializers.ReadOnlyField()
    budget_utilization = serializers.ReadOnlyField()
    milestones = MilestoneSerializer(many=True, read_only=True)
    team_member_details = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "code", "name", "description",
            "status", "priority",
            "department", "department_name",
            "project_manager", "project_manager_name",
            "team_members", "team_member_details",
            "client_name", "start_date", "end_date", "actual_end_date",
            "budget", "spent_budget", "remaining_budget",
            "budget_utilization", "hourly_rate", "is_billable",
            "progress", "total_hours", "total_billable_amount",
            "tags", "notes", "milestones",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "spent_budget", "progress",
            "created_by", "created_at", "updated_at",
        ]

    def get_team_member_details(self, obj):
        return [
            {
                "id": str(member.id),
                "name": member.full_name,
                "email": member.email,
                "job_title": member.job_title,
            }
            for member in obj.team_members.all()
        ]

    def create(self, validated_data):
        team_members = validated_data.pop("team_members", [])
        organization = self.context["request"].user.organization
        user = self.context["request"].user

        project = Project.objects.create(
            organization=organization,
            created_by=user,
            **validated_data,
        )
        if team_members:
            project.team_members.set(team_members)
        return project
