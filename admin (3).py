"""
Accounts serializers for authentication, user management, and organization setup.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Department, Organization, Role, RolePermission

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user data."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["full_name"] = user.full_name
        token["is_org_admin"] = user.is_org_admin
        if user.organization:
            token["organization_id"] = str(user.organization.id)
            token["organization_name"] = user.organization.name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = ["id", "module", "permission"]
        read_only_fields = ["id"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True, read_only=True)
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id", "name", "description", "is_system_role",
            "permissions", "user_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system_role", "created_at", "updated_at"]

    def get_user_count(self, obj):
        return obj.users.filter(is_active=True).count()


class RoleWriteSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        permissions_data = validated_data.pop("permissions", [])
        organization = self.context["request"].user.organization
        role = Role.objects.create(organization=organization, **validated_data)
        for perm_data in permissions_data:
            RolePermission.objects.create(role=role, **perm_data)
        return role

    def update(self, instance, validated_data):
        permissions_data = validated_data.pop("permissions", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if permissions_data is not None:
            instance.permissions.all().delete()
            for perm_data in permissions_data:
                RolePermission.objects.create(role=instance, **perm_data)
        return instance


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.CharField(source="head.full_name", read_only=True)
    employee_count = serializers.ReadOnlyField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            "id", "name", "code", "description", "parent",
            "head", "head_name", "budget", "is_active",
            "employee_count", "children", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return DepartmentSerializer(children, many=True).data

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Department.objects.create(organization=organization, **validated_data)


class OrganizationSerializer(serializers.ModelSerializer):
    active_users_count = serializers.ReadOnlyField()
    departments_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "domain", "logo", "address",
            "city", "state", "country", "postal_code", "phone",
            "email", "website", "tax_id", "currency", "timezone",
            "subscription_plan", "max_users", "is_active",
            "active_users_count", "departments_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_departments_count(self, obj):
        return obj.departments.filter(is_active=True).count()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    department_name = serializers.CharField(
        source="department.name", read_only=True
    )
    role_name = serializers.CharField(source="role.name", read_only=True)
    accessible_modules = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "phone", "avatar", "organization", "organization_name",
            "department", "department_name", "role", "role_name",
            "job_title", "is_active", "is_org_admin",
            "accessible_modules", "date_joined", "last_login",
        ]
        read_only_fields = [
            "id", "date_joined", "last_login",
        ]

    def get_accessible_modules(self, obj):
        return obj.get_accessible_modules()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "phone",
            "department", "role", "job_title", "password",
            "password_confirm", "is_org_admin",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        organization = self.context["request"].user.organization
        if organization:
            active_count = organization.active_users_count
            if active_count >= organization.max_users:
                raise serializers.ValidationError(
                    "Maximum number of users reached for this organization."
                )
        return attrs

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        user = User.objects.create_user(
            organization=organization,
            **validated_data,
        )
        return user


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
