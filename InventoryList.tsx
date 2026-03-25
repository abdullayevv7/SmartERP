"""
Custom pagination classes for SmartERP API.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination with customizable page size."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "example": 123,
                },
                "total_pages": {
                    "type": "integer",
                    "example": 5,
                },
                "current_page": {
                    "type": "integer",
                    "example": 1,
                },
                "page_size": {
                    "type": "integer",
                    "example": 25,
                },
                "next": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "example": "http://api.example.org/items/?page=2",
                },
                "previous": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "example": "http://api.example.org/items/?page=1",
                },
                "results": schema,
            },
        }


class LargeResultsSetPagination(PageNumberPagination):
    """Pagination for endpoints expected to return large datasets."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


class SmallResultsSetPagination(PageNumberPagination):
    """Pagination for endpoints returning smaller datasets like dropdowns."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50
