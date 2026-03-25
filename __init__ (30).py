"""
Procurement serializers.
"""

from rest_framework import serializers

from .models import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequest,
    PurchaseRequestItem,
    Supplier,
)


class SupplierSerializer(serializers.ModelSerializer):
    total_orders = serializers.ReadOnlyField()
    total_spend = serializers.ReadOnlyField()

    class Meta:
        model = Supplier
        fields = [
            "id", "code", "name", "contact_person", "email",
            "phone", "website", "address", "city", "country",
            "tax_id", "payment_terms", "currency", "rating",
            "notes", "is_active",
            "total_orders", "total_spend",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Supplier.objects.create(
            organization=organization, **validated_data
        )


class PurchaseRequestItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name", read_only=True
    )

    class Meta:
        model = PurchaseRequestItem
        fields = [
            "id", "product", "product_name", "description",
            "quantity", "estimated_unit_price", "estimated_total",
        ]
        read_only_fields = ["id", "estimated_total"]


class PurchaseRequestSerializer(serializers.ModelSerializer):
    items = PurchaseRequestItemSerializer(many=True, read_only=True)
    requested_by_name = serializers.CharField(
        source="requested_by.full_name", read_only=True
    )
    approved_by_name = serializers.CharField(
        source="approved_by.full_name", read_only=True
    )
    department_name = serializers.CharField(
        source="department.name", read_only=True
    )

    class Meta:
        model = PurchaseRequest
        fields = [
            "id", "reference", "requested_by", "requested_by_name",
            "department", "department_name", "title", "description",
            "priority", "status", "estimated_cost", "required_date",
            "approved_by", "approved_by_name", "approved_at",
            "rejection_reason", "notes", "items",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "requested_by", "approved_by", "approved_at",
            "rejection_reason", "created_at", "updated_at",
        ]


class PurchaseRequestWriteSerializer(serializers.ModelSerializer):
    items = PurchaseRequestItemSerializer(many=True)

    class Meta:
        model = PurchaseRequest
        fields = [
            "id", "reference", "department", "title",
            "description", "priority", "estimated_cost",
            "required_date", "notes", "items",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        organization = self.context["request"].user.organization
        user = self.context["request"].user

        pr = PurchaseRequest.objects.create(
            organization=organization,
            requested_by=user,
            **validated_data,
        )

        for item_data in items_data:
            PurchaseRequestItem.objects.create(
                purchase_request=pr, **item_data
            )

        return pr

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PurchaseRequestItem.objects.create(
                    purchase_request=instance, **item_data
                )

        return instance


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name", read_only=True
    )
    is_fully_received = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id", "product", "product_name", "description",
            "quantity_ordered", "quantity_received",
            "unit_price", "total", "is_fully_received",
        ]
        read_only_fields = ["id", "total"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(
        source="supplier.name", read_only=True
    )
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True
    )
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True
    )

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "order_number", "supplier", "supplier_name",
            "purchase_request", "status",
            "order_date", "expected_delivery_date", "actual_delivery_date",
            "subtotal", "tax_amount", "shipping_cost",
            "discount_amount", "total_amount", "currency",
            "payment_terms", "shipping_address",
            "warehouse", "warehouse_name", "notes",
            "created_by", "created_by_name",
            "approved_by", "items",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "subtotal", "total_amount",
            "created_by", "created_at", "updated_at",
        ]


class PurchaseOrderWriteSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "order_number", "supplier", "purchase_request",
            "order_date", "expected_delivery_date",
            "tax_amount", "shipping_cost", "discount_amount",
            "currency", "payment_terms", "shipping_address",
            "warehouse", "notes", "items",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        organization = self.context["request"].user.organization
        user = self.context["request"].user

        po = PurchaseOrder.objects.create(
            organization=organization,
            created_by=user,
            **validated_data,
        )

        for item_data in items_data:
            PurchaseOrderItem.objects.create(
                purchase_order=po, **item_data
            )

        po.calculate_totals()
        return po
