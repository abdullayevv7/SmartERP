"""
Accounts views for authentication, user management, organizations, departments, and roles.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from utils.mixins import TenantQuerySetMixin
from utils.permissions import IsOrgAdmin

from .models import Department, Organization, Role
from .permissions import HasModulePermission
from .serializers import (
    CustomTokenObtainPairSerializer,
    DepartmentSerializer,
    OrganizationSerializer,
    PasswordChangeSerializer,
    RoleSerializer,
    RoleWriteSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login endpoint returning JWT tokens with user data."""

    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """Token refresh endpoint."""

    pass


class LogoutView(generics.GenericAPIView):
    """Blacklist the refresh token on logout."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RegisterView(generics.CreateAPIView):
    """Register a new organization and admin user."""

    permission_classes = [permissions.AllowAny]
    serializer_class = UserCreateSerializer

    def create(self, request, *args, **kwargs):
        org_data = {
            "name": request.data.get("organization_name", ""),
            "slug": request.data.get("organization_slug", ""),
        }
        if not org_data["name"]:
            return Response(
                {"organization_name": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        organization = Organization.objects.create(**org_data)

        user_data = {
            "email": request.data.get("email"),
            "first_name": request.data.get("first_name", ""),
            "last_name": request.data.get("last_name", ""),
            "password": request.data.get("password"),
        }
        user = User.objects.create_user(
            organization=organization,
            is_org_admin=True,
            **user_data,
        )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the current authenticated user's profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.GenericAPIView):
    """Change the current user's password."""

    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.password_changed_at = timezone.now()
        user.save()
        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


class UserViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for users within the current organization."""

    permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]
    filterset_fields = ["department", "role", "is_active", "is_org_admin"]
    search_fields = ["email", "first_name", "last_name", "job_title"]
    ordering_fields = ["first_name", "last_name", "date_joined"]

    def get_queryset(self):
        return User.objects.filter(
            organization=self.request.user.organization
        ).select_related("department", "role", "organization")

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response(
                {"detail": "You cannot deactivate yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.save()
        return Response({"detail": "User deactivated."})

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({"detail": "User activated."})


class OrganizationView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the current user's organization."""

    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]

    def get_object(self):
        return self.request.user.organization


class DepartmentViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for departments within the current organization."""

    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "accounts"
    filterset_fields = ["is_active", "parent"]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "code"]

    def get_queryset(self):
        return Department.objects.filter(
            organization=self.request.user.organization
        ).select_related("head", "parent")


class RoleViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for roles within the current organization."""

    permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return Role.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related("permissions")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return RoleWriteSerializer
        return RoleSerializer

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.is_system_role:
            return Response(
                {"detail": "System roles cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
