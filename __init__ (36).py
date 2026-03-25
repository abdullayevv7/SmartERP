"""
Projects URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MilestoneViewSet,
    ProjectViewSet,
    TaskViewSet,
    TimeEntryViewSet,
)

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"milestones", MilestoneViewSet, basename="milestone")
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"time-entries", TimeEntryViewSet, basename="time-entry")

urlpatterns = [
    path("", include(router.urls)),
]
