"""
Inventory serializers for warehouses, products, stock levels, and movements.
"""

from rest_framework import serializers

from .models import (
    Product,
    ProductCategory,
    StockLevel,
    StockMovement,
    Warehouse,
)


class WarehouseSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(
        source="manager.full_name", read_only=True
    )
    total_stock_value = serializers.ReadOnlyField()
    stock_count = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = [
            "id", "name", "code", "warehouse_type",
            "address", "city", "state", "country", "postal_code",
            "latitude", "longitude",
            "manager", "manager_name", "capacity",
            "phone", "email", "is_active",
            "total_stock_value", "stock_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_stock_count(self, obj):
        return obj.stock_levels.filter(quantity__gt=0).count()

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Warehouse.objects.create(
            organization=organization, **validated_data
        )


class ProductCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = [
            "id", "name", "code", "parent", "description",
            "is_active", "children", "product_count",
        ]
        read_only_fields = ["id"]

    def get_children(self, obj):
        return ProductCategorySerializer(
            obj.children.filter(is_active=True), many=True
        ).data

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return ProductCategory.objects.create(
            organization=organization, **validated_data
        )


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight product serializer for list views."""

    category_name = serializers.CharField(
        source="category.name", read_only=True
    )
    total_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    stock_value = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id", "sku", "barcode", "name", "category",
            "category_name", "product_type", "unit_of_measure",
            "unit_cost", "unit_price",
            "total_stock", "is_low_stock", "stock_value",
            "min_stock_level", "is_active",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed product serializer."""

    category_name = serializers.CharField(
        source="category.name", read_only=True
    )
    total_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    stock_value = serializers.ReadOnlyField()
    stock_by_warehouse = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "sku", "barcode", "name", "description",
            "category", "category_name", "product_type",
            "unit_of_measure", "unit_cost", "unit_price",
            "min_stock_level", "reorder_quantity", "max_stock_level",
            "weight", "image", "is_active", "is_trackable",
            "total_stock", "is_low_stock", "stock_value",
            "stock_by_warehouse",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_stock_by_warehouse(self, obj):
        return list(
            obj.stock_levels.select_related("warehouse").values(
                "warehouse__name",
                "warehouse__code",
                "quantity",
                "reserved_quantity",
            )
        )

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Product.objects.create(
            organization=organization, **validated_data
        )


class StockLevelSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True
    )
    available_quantity = serializers.ReadOnlyField()

    class Meta:
        model = StockLevel
        fields = [
            "id", "product", "product_name", "product_sku",
            "warehouse", "warehouse_name",
            "quantity", "reserved_quantity", "available_quantity",
            "last_counted_at", "last_movement_at", "updated_at",
        ]
        read_only_fields = [
            "id", "last_movement_at", "updated_at",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    source_warehouse_name = serializers.CharField(
        source="source_warehouse.name", read_only=True
    )
    destination_warehouse_name = serializers.CharField(
        source="destination_warehouse.name", read_only=True
    )
    performed_by_name = serializers.CharField(
        source="performed_by.full_name", read_only=True
    )

    class Meta:
        model = StockMovement
        fields = [
            "id", "reference", "movement_type",
            "product", "product_name", "product_sku",
            "source_warehouse", "source_warehouse_name",
            "destination_warehouse", "destination_warehouse_name",
            "quantity", "unit_cost", "total_cost",
            "status", "reason",
            "related_purchase_order", "related_sales_order",
            "performed_by", "performed_by_name",
            "completed_at", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "total_cost", "performed_by",
            "completed_at", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        movement_type = attrs.get("movement_type")

        if movement_type in ("outbound", "transfer") and not attrs.get("source_warehouse"):
            raise serializers.ValidationError(
                {"source_warehouse": "Source warehouse is required for outbound/transfer."}
            )

        if movement_type in ("inbound", "transfer") and not attrs.get("destination_warehouse"):
            raise serializers.ValidationError(
                {"destination_warehouse": "Destination warehouse is required for inbound/transfer."}
            )

        if movement_type == "transfer":
            if attrs.get("source_warehouse") == attrs.get("destination_warehouse"):
                raise serializers.ValidationError(
                    "Source and destination warehouses must be different."
                )

        return attrs

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return StockMovement.objects.create(
            organization=organization, **validated_data
        )
