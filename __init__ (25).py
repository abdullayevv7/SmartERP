"""
Inventory URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ProductCategoryViewSet,
    ProductViewSet,
    StockLevelViewSet,
    StockMovementViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()
router.register(r"warehouses", WarehouseViewSet, basename="warehouse")
router.register(r"categories", ProductCategoryViewSet, basename="product-category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"stock-levels", StockLevelViewSet, basename="stock-level")
router.register(r"movements", StockMovementViewSet, basename="stock-movement")

urlpatterns = [
    path("", include(router.urls)),
]
