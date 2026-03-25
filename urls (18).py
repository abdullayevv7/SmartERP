"""
HR URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceViewSet,
    EmployeeViewSet,
    LeaveRequestViewSet,
    PayrollViewSet,
    PositionViewSet,
)

router = DefaultRouter()
router.register(r"positions", PositionViewSet, basename="position")
router.register(r"employees", EmployeeViewSet, basename="employee")
router.register(r"leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register(r"attendance", AttendanceViewSet, basename="attendance")
router.register(r"payroll", PayrollViewSet, basename="payroll")

urlpatterns = [
    path("", include(router.urls)),
]
