"""
Sales URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomerViewSet,
    QuotationViewSet,
    SalesOrderViewSet,
    SalesReportViewSet,
)

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"quotations", QuotationViewSet, basename="quotation")
router.register(r"orders", SalesOrderViewSet, basename="sales-order")
router.register(r"reports", SalesReportViewSet, basename="sales-report")

urlpatterns = [
    path("", include(router.urls)),
]
