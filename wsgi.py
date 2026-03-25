"""
Sales serializers.
"""

from rest_framework import serializers

from .models import (
    Customer,
    Quotation,
    QuotationItem,
    SalesOrder,
    SalesOrderItem,
    SalesReport,
)


class CustomerSerializer(serializers.ModelSerializer):
    total_revenue = serializers.ReadOnlyField()
    outstanding_balance = serializers.ReadOnlyField()
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True
    )

    class Meta:
        model = Customer
        fields = [
            "id", "code", "name", "customer_type",
            "contact_person", "email", "phone", "website",
            "address", "shipping_address", "city", "country",
            "tax_id", "credit_limit", "payment_terms",
            "currency", "assigned_to", "assigned_to_name",
            "notes", "is_active",
            "total_revenue", "outstanding_balance",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Customer.objects.create(
            organization=organization, **validated_data
        )


class QuotationItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name", read_only=True
    )

    class Meta:
        model = QuotationItem
        fields = [
            "id", "product", "product_name", "description",
            "quantity", "unit_price", "total",
        ]
        read_only_fields = ["id", "total"]


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(
        source="customer.name", read_only=True
    )
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True
    )

    class Meta:
        model = Quotation
        fields = [
            "id", "quotation_number", "customer", "customer_name",
            "status", "issue_date", "valid_until",
            "subtotal", "tax_rate", "tax_amount",
            "discount_amount", "total_amount", "currency",
            "terms", "notes",
            "created_by", "created_by_name",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "subtotal", "tax_amount", "total_amount",
            "created_by", "created_at", "updated_at",
        ]


class QuotationWriteSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True)

    class Meta:
        model = Quotation
        fields = [
            "id", "quotation_number", "customer",
            "issue_date", "valid_until",
            "tax_rate", "discount_amount", "currency",
            "terms", "notes", "items",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        organization = self.context["request"].user.organization
        user = self.context["request"].user

        quotation = Quotation.objects.create(
            organization=organization,
            created_by=user,
            **validated_data,
        )

        for item_data in items_data:
            QuotationItem.objects.create(quotation=quotation, **item_data)

        quotation.calculate_totals()
        return quotation


class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name", read_only=True
    )

    class Meta:
        model = SalesOrderItem
        fields = [
            "id", "product", "product_name", "description",
            "quantity", "unit_price", "total",
        ]
        read_only_fields = ["id", "total"]


class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(
        source="customer.name", read_only=True
    )
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True
    )
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True
    )

    class Meta:
        model = SalesOrder
        fields = [
            "id", "order_number", "customer", "customer_name",
            "quotation", "status", "payment_status",
            "order_date", "expected_delivery_date", "actual_delivery_date",
            "subtotal", "tax_rate", "tax_amount",
            "shipping_cost", "discount_amount", "total_amount",
            "amount_paid", "currency", "shipping_address",
            "notes", "warehouse", "warehouse_name",
            "created_by", "created_by_name",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "subtotal", "tax_amount", "total_amount",
            "created_by", "created_at", "updated_at",
        ]


class SalesOrderWriteSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True)

    class Meta:
        model = SalesOrder
        fields = [
            "id", "order_number", "customer", "quotation",
            "order_date", "expected_delivery_date",
            "tax_rate", "shipping_cost", "discount_amount",
            "currency", "shipping_address",
            "notes", "warehouse", "items",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        organization = self.context["request"].user.organization
        user = self.context["request"].user

        order = SalesOrder.objects.create(
            organization=organization,
            created_by=user,
            **validated_data,
        )

        for item_data in items_data:
            SalesOrderItem.objects.create(sales_order=order, **item_data)

        order.calculate_totals()
        return order


class SalesReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesReport
        fields = [
            "id", "report_type", "period_start", "period_end",
            "total_orders", "total_revenue", "total_cost",
            "gross_profit", "new_customers", "returning_customers",
            "average_order_value", "top_products", "top_customers",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
