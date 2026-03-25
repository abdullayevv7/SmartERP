"""
Accounts URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    DepartmentViewSet,
    LogoutView,
    MeView,
    OrganizationView,
    PasswordChangeView,
    RegisterView,
    RoleViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"roles", RoleViewSet, basename="role")

urlpatterns = [
    # Authentication
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    # Profile
    path("me/", MeView.as_view(), name="me"),
    path("me/password/", PasswordChangeView.as_view(), name="password-change"),
    # Organization
    path("organization/", OrganizationView.as_view(), name="organization"),
    # Router URLs
    path("", include(router.urls)),
]
