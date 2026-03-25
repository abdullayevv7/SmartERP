"""
Procurement views for suppliers, purchase requests, and purchase orders.
"""

from django.db.models import Avg, Count, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from utils.mixins import TenantQuerySetMixin

from .models import PurchaseOrder, PurchaseOrderItem, PurchaseRequest, Supplier
from .serializers import (
    PurchaseOrderSerializer,
    PurchaseOrderWriteSerializer,
    PurchaseRequestSerializer,
    PurchaseRequestWriteSerializer,
    SupplierSerializer,
)


class SupplierViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for suppliers."""

    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "procurement"
    filterset_fields = ["is_active", "rating", "country"]
    search_fields = ["code", "name", "contact_person", "email"]
    ordering_fields = ["name", "rating", "created_at"]

    def get_queryset(self):
        return Supplier.objects.filter(
            organization=self.request.user.organization
        )

    @action(detail=True, methods=["get"])
    def performance(self, request, pk=None):
        """Get supplier performance metrics."""
        supplier = self.get_object()
        orders = supplier.purchase_orders.all()

        on_time = orders.filter(
            status="received",
            actual_delivery_date__lte=models.F("expected_delivery_date"),
        ).count()
        total_delivered = orders.filter(status="received").count()

        return Response({
            "total_orders": orders.count(),
            "total_spend": supplier.total_spend,
            "delivered": total_delivered,
            "on_time_delivery_rate": (
                round(on_time / total_delivered * 100, 1)
                if total_delivered > 0 else 0
            ),
            "average_rating": supplier.rating,
            "by_status": list(
                orders.values("status")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
        })


class PurchaseRequestViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for purchase requests."""

    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "procurement"
    filterset_fields = ["status", "priority", "department", "requested_by"]
    search_fields = ["reference", "title"]
    ordering_fields = ["created_at", "required_date", "estimated_cost"]

    def get_queryset(self):
        return PurchaseRequest.objects.filter(
            organization=self.request.user.organization
        ).select_related(
            "requested_by", "approved_by", "department"
        ).prefetch_related("items")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PurchaseRequestWriteSerializer
        return PurchaseRequestSerializer

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a purchase request."""
        pr = self.get_object()
        if pr.status != "submitted":
            return Response(
                {"detail": "Only submitted requests can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pr.status = "approved"
        pr.approved_by = request.user
        pr.approved_at = timezone.now()
        pr.save()
        return Response(PurchaseRequestSerializer(pr).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a purchase request."""
        pr = self.get_object()
        if pr.status != "submitted":
            return Response(
                {"detail": "Only submitted requests can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pr.status = "rejected"
        pr.approved_by = request.user
        pr.approved_at = timezone.now()
        pr.rejection_reason = request.data.get("reason", "")
        pr.save()
        return Response(PurchaseRequestSerializer(pr).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a draft purchase request for approval."""
        pr = self.get_object()
        if pr.status != "draft":
            return Response(
                {"detail": "Only draft requests can be submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pr.status = "submitted"
        pr.save()
        return Response(PurchaseRequestSerializer(pr).data)


class PurchaseOrderViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for purchase orders."""

    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "procurement"
    filterset_fields = ["status", "supplier"]
    search_fields = ["order_number", "supplier__name"]
    ordering_fields = ["order_date", "total_amount", "created_at"]

    def get_queryset(self):
        return PurchaseOrder.objects.filter(
            organization=self.request.user.organization
        ).select_related(
            "supplier", "created_by", "warehouse"
        ).prefetch_related("items")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PurchaseOrderWriteSerializer
        return PurchaseOrderSerializer

    @action(detail=True, methods=["post"])
    def send_to_supplier(self, request, pk=None):
        """Mark the PO as sent to supplier."""
        po = self.get_object()
        if po.status != "draft":
            return Response(
                {"detail": "Only draft POs can be sent."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        po.status = "sent"
        po.save()
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        """Record goods receipt for a purchase order."""
        po = self.get_object()
        if po.status not in ("confirmed", "partially_received"):
            return Response(
                {"detail": "PO must be confirmed to receive goods."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_received = request.data.get("items", [])
        if not items_received:
            return Response(
                {"detail": "No items provided for receipt."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for item_data in items_received:
            try:
                item = PurchaseOrderItem.objects.get(
                    id=item_data["item_id"],
                    purchase_order=po,
                )
                qty = int(item_data.get("quantity", 0))
                if qty > 0:
                    item.quantity_received += qty
                    item.save()
            except (PurchaseOrderItem.DoesNotExist, KeyError, ValueError):
                continue

        # Check if all items are fully received
        all_received = all(
            item.is_fully_received for item in po.items.all()
        )
        if all_received:
            po.status = "received"
            po.actual_delivery_date = timezone.now().date()
        else:
            po.status = "partially_received"
        po.save()

        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Procurement dashboard data."""
        qs = self.get_queryset()
        today = timezone.now().date()
        month_start = today.replace(day=1)

        return Response({
            "total_orders": qs.count(),
            "pending_orders": qs.filter(
                status__in=["draft", "sent", "confirmed"]
            ).count(),
            "monthly_spend": qs.filter(
                order_date__gte=month_start,
                status__in=["received", "partially_received"],
            ).aggregate(total=Sum("total_amount"))["total"] or 0,
            "pending_requests": PurchaseRequest.objects.filter(
                organization=request.user.organization,
                status="submitted",
            ).count(),
            "by_status": list(
                qs.values("status")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "top_suppliers": list(
                qs.filter(status="received")
                .values("supplier__name")
                .annotate(
                    order_count=Count("id"),
                    total_spend=Sum("total_amount"),
                )
                .order_by("-total_spend")[:5]
            ),
        })
