"""
Inventory views for warehouses, products, stock levels, and movements.
"""

from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from utils.mixins import TenantQuerySetMixin

from .models import (
    Product,
    ProductCategory,
    StockLevel,
    StockMovement,
    Warehouse,
)
from .serializers import (
    ProductCategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    StockLevelSerializer,
    StockMovementSerializer,
    WarehouseSerializer,
)


class WarehouseViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for warehouses."""

    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "inventory"
    filterset_fields = ["warehouse_type", "is_active", "city", "country"]
    search_fields = ["name", "code", "city"]
    ordering_fields = ["name", "code"]

    def get_queryset(self):
        return Warehouse.objects.filter(
            organization=self.request.user.organization
        ).select_related("manager")

    @action(detail=True, methods=["get"])
    def stock(self, request, pk=None):
        """List all stock levels for a warehouse."""
        warehouse = self.get_object()
        stock_levels = StockLevel.objects.filter(
            warehouse=warehouse, quantity__gt=0
        ).select_related("product")
        serializer = StockLevelSerializer(stock_levels, many=True)
        return Response(serializer.data)


class ProductCategoryViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for product categories."""

    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "inventory"
    filterset_fields = ["is_active", "parent"]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return ProductCategory.objects.filter(
            organization=self.request.user.organization
        )

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Return categories as a tree structure."""
        categories = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)


class ProductViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for products."""

    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "inventory"
    filterset_fields = [
        "category", "product_type", "is_active", "is_trackable",
    ]
    search_fields = ["sku", "barcode", "name"]
    ordering_fields = ["sku", "name", "unit_price", "unit_cost"]

    def get_queryset(self):
        return Product.objects.filter(
            organization=self.request.user.organization
        ).select_related("category")

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        return ProductDetailSerializer

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """List products below minimum stock level."""
        products = self.get_queryset().filter(
            is_active=True, is_trackable=True
        )
        low_stock_products = []
        for product in products:
            if product.is_low_stock:
                low_stock_products.append({
                    "id": str(product.id),
                    "sku": product.sku,
                    "name": product.name,
                    "total_stock": product.total_stock,
                    "min_stock_level": product.min_stock_level,
                    "reorder_quantity": product.reorder_quantity,
                    "deficit": product.min_stock_level - product.total_stock,
                })
        return Response(low_stock_products)

    @action(detail=False, methods=["get"])
    def valuation(self, request):
        """Stock valuation summary."""
        products = self.get_queryset().filter(
            is_active=True, is_trackable=True
        )
        total_value = sum(p.stock_value for p in products)
        by_category = {}
        for product in products:
            cat_name = product.category.name if product.category else "Uncategorized"
            if cat_name not in by_category:
                by_category[cat_name] = {"count": 0, "value": 0}
            by_category[cat_name]["count"] += 1
            by_category[cat_name]["value"] += float(product.stock_value)

        return Response({
            "total_products": products.count(),
            "total_value": total_value,
            "by_category": by_category,
        })


class StockLevelViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for stock levels."""

    serializer_class = StockLevelSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "inventory"
    filterset_fields = ["product", "warehouse"]
    search_fields = ["product__name", "product__sku", "warehouse__name"]
    ordering_fields = ["quantity", "updated_at"]

    def get_queryset(self):
        return StockLevel.objects.filter(
            organization=self.request.user.organization
        ).select_related("product", "warehouse")

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        """Manually adjust stock level with a stock adjustment movement."""
        stock_level = self.get_object()
        new_quantity = request.data.get("quantity")
        reason = request.data.get("reason", "Manual stock adjustment")

        if new_quantity is None:
            return Response(
                {"detail": "Quantity is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_quantity = int(new_quantity)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid quantity."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        difference = new_quantity - stock_level.quantity

        # Create adjustment movement
        movement = StockMovement.objects.create(
            organization=request.user.organization,
            reference=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            movement_type="adjustment",
            product=stock_level.product,
            destination_warehouse=stock_level.warehouse if difference > 0 else None,
            source_warehouse=stock_level.warehouse if difference < 0 else None,
            quantity=abs(difference),
            reason=reason,
            status="completed",
            performed_by=request.user,
            completed_at=timezone.now(),
        )

        stock_level.quantity = new_quantity
        stock_level.last_counted_at = timezone.now()
        stock_level.last_movement_at = timezone.now()
        stock_level.save()

        return Response(StockLevelSerializer(stock_level).data)


class StockMovementViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for stock movements."""

    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "inventory"
    filterset_fields = [
        "movement_type", "status", "product",
        "source_warehouse", "destination_warehouse",
    ]
    search_fields = ["reference", "product__name", "product__sku"]
    ordering_fields = ["created_at", "completed_at"]

    def get_queryset(self):
        return StockMovement.objects.filter(
            organization=self.request.user.organization
        ).select_related(
            "product", "source_warehouse",
            "destination_warehouse", "performed_by",
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Complete a pending stock movement."""
        movement = self.get_object()
        try:
            movement.complete(request.user)
            return Response(
                StockMovementSerializer(movement).data,
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a pending stock movement."""
        movement = self.get_object()
        if movement.status not in ("pending", "in_transit"):
            return Response(
                {"detail": "Only pending/in-transit movements can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        movement.status = "cancelled"
        movement.save()
        return Response(StockMovementSerializer(movement).data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Inventory movement statistics."""
        qs = self.get_queryset()
        today = timezone.now().date()
        month_start = today.replace(day=1)

        monthly = qs.filter(
            created_at__date__gte=month_start,
            status="completed",
        )

        return Response({
            "total_movements": monthly.count(),
            "by_type": list(
                monthly.values("movement_type")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "total_inbound": monthly.filter(
                movement_type="inbound"
            ).aggregate(total=Sum("quantity"))["total"] or 0,
            "total_outbound": monthly.filter(
                movement_type="outbound"
            ).aggregate(total=Sum("quantity"))["total"] or 0,
            "pending_movements": qs.filter(
                status__in=["pending", "in_transit"]
            ).count(),
        })
