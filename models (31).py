"""
Procurement URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PurchaseOrderViewSet,
    PurchaseRequestViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register(r"suppliers", SupplierViewSet, basename="supplier")
router.register(r"requests", PurchaseRequestViewSet, basename="purchase-request")
router.register(r"orders", PurchaseOrderViewSet, basename="purchase-order")

urlpatterns = [
    path("", include(router.urls)),
]
