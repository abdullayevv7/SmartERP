"""
Inventory admin configuration.
"""

from django.contrib import admin

from .models import (
    Product,
    ProductCategory,
    StockLevel,
    StockMovement,
    Warehouse,
)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = [
        "name", "code", "warehouse_type", "city",
        "manager", "is_active", "organization",
    ]
    list_filter = ["organization", "warehouse_type", "is_active"]
    search_fields = ["name", "code"]


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "parent", "is_active", "organization"]
    list_filter = ["organization", "is_active"]
    search_fields = ["name", "code"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "sku", "name", "category", "product_type",
        "unit_cost", "unit_price", "min_stock_level",
        "is_active", "organization",
    ]
    list_filter = ["organization", "product_type", "category", "is_active"]
    search_fields = ["sku", "barcode", "name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = [
        "product", "warehouse", "quantity",
        "reserved_quantity", "last_movement_at",
    ]
    list_filter = ["organization", "warehouse"]
    search_fields = ["product__sku", "product__name"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        "reference", "movement_type", "product", "quantity",
        "source_warehouse", "destination_warehouse",
        "status", "performed_by", "created_at",
    ]
    list_filter = ["organization", "movement_type", "status"]
    search_fields = ["reference", "product__sku"]
    readonly_fields = ["created_at", "updated_at"]
