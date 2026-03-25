"""
Custom exception handling for SmartERP API.
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error response format.

    Response format:
    {
        "error": {
            "code": "error_code",
            "message": "Human readable message",
            "details": {} or []  # Optional additional details
        }
    }
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "error": {
                "code": _get_error_code(exc),
                "message": _get_error_message(exc, response),
                "status_code": response.status_code,
            }
        }

        # Include field-level validation errors
        if isinstance(response.data, dict):
            field_errors = {}
            for key, value in response.data.items():
                if key not in ("detail", "non_field_errors"):
                    field_errors[key] = (
                        value if isinstance(value, list) else [str(value)]
                    )
            if field_errors:
                error_data["error"]["details"] = field_errors

        # Include non-field errors
        if isinstance(response.data, dict) and "non_field_errors" in response.data:
            error_data["error"]["non_field_errors"] = response.data["non_field_errors"]

        response.data = error_data

    else:
        # Handle unexpected exceptions
        if isinstance(exc, Http404):
            response = Response(
                {
                    "error": {
                        "code": "not_found",
                        "message": "The requested resource was not found.",
                        "status_code": 404,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        elif isinstance(exc, PermissionDenied):
            response = Response(
                {
                    "error": {
                        "code": "permission_denied",
                        "message": "You do not have permission to perform this action.",
                        "status_code": 403,
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        elif isinstance(exc, ValidationError):
            response = Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": str(exc),
                        "status_code": 400,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            logger.exception(f"Unhandled exception: {exc}")
            response = Response(
                {
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected error occurred. Please try again later.",
                        "status_code": 500,
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return response


def _get_error_code(exc):
    """Map exception to error code."""
    code_map = {
        "NotAuthenticated": "not_authenticated",
        "AuthenticationFailed": "authentication_failed",
        "PermissionDenied": "permission_denied",
        "NotFound": "not_found",
        "MethodNotAllowed": "method_not_allowed",
        "ValidationError": "validation_error",
        "ParseError": "parse_error",
        "Throttled": "rate_limited",
    }
    class_name = exc.__class__.__name__
    return code_map.get(class_name, "error")


def _get_error_message(exc, response):
    """Extract human-readable error message."""
    if hasattr(exc, "detail"):
        if isinstance(exc.detail, str):
            return exc.detail
        elif isinstance(exc.detail, dict):
            if "detail" in exc.detail:
                return str(exc.detail["detail"])
        elif isinstance(exc.detail, list):
            return "; ".join(str(d) for d in exc.detail)
    return "An error occurred."


class BusinessLogicError(APIException):
    """Exception for business logic violations."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "The request could not be processed due to a business rule violation."
    default_code = "business_logic_error"


class ConflictError(APIException):
    """Exception for resource conflicts."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state of the resource."
    default_code = "conflict"


class QuotaExceededError(APIException):
    """Exception for quota exceeded scenarios."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Your organization has exceeded its quota for this resource."
    default_code = "quota_exceeded"
