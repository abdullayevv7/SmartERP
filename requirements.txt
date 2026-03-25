"""
Sales views for customers, quotations, sales orders, and reports.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from utils.mixins import TenantQuerySetMixin

from .models import Customer, Quotation, SalesOrder, SalesReport
from .serializers import (
    CustomerSerializer,
    QuotationSerializer,
    QuotationWriteSerializer,
    SalesOrderSerializer,
    SalesOrderWriteSerializer,
    SalesReportSerializer,
)


class CustomerViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for customers."""

    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "sales"
    filterset_fields = ["customer_type", "is_active", "assigned_to", "country"]
    search_fields = ["code", "name", "contact_person", "email"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return Customer.objects.filter(
            organization=self.request.user.organization
        ).select_related("assigned_to")

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Customer order history."""
        customer = self.get_object()
        orders = customer.sales_orders.all().order_by("-order_date")[:20]
        return Response(SalesOrderSerializer(orders, many=True).data)


class QuotationViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for quotations."""

    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "sales"
    filterset_fields = ["status", "customer"]
    search_fields = ["quotation_number", "customer__name"]
    ordering_fields = ["issue_date", "total_amount"]

    def get_queryset(self):
        return Quotation.objects.filter(
            organization=self.request.user.organization
        ).select_related("customer", "created_by").prefetch_related("items")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return QuotationWriteSerializer
        return QuotationSerializer

    @action(detail=True, methods=["post"])
    def convert_to_order(self, request, pk=None):
        """Convert an accepted quotation to a sales order."""
        quotation = self.get_object()
        if quotation.status != "accepted":
            return Response(
                {"detail": "Only accepted quotations can be converted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate order number
        last_order = SalesOrder.objects.filter(
            organization=request.user.organization,
        ).order_by("-created_at").first()
        if last_order:
            try:
                num = int(last_order.order_number.split("-")[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        order_number = f"SO-{num:06d}"

        order = SalesOrder.objects.create(
            organization=request.user.organization,
            order_number=order_number,
            customer=quotation.customer,
            quotation=quotation,
            order_date=timezone.now().date(),
            subtotal=quotation.subtotal,
            tax_rate=quotation.tax_rate,
            tax_amount=quotation.tax_amount,
            discount_amount=quotation.discount_amount,
            total_amount=quotation.total_amount,
            currency=quotation.currency,
            created_by=request.user,
        )

        # Copy line items
        from .models import SalesOrderItem

        for item in quotation.items.all():
            SalesOrderItem.objects.create(
                sales_order=order,
                product=item.product,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total=item.total,
            )

        return Response(
            SalesOrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class SalesOrderViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for sales orders."""

    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "sales"
    filterset_fields = ["status", "payment_status", "customer"]
    search_fields = ["order_number", "customer__name"]
    ordering_fields = ["order_date", "total_amount"]

    def get_queryset(self):
        return SalesOrder.objects.filter(
            organization=self.request.user.organization
        ).select_related(
            "customer", "created_by", "warehouse"
        ).prefetch_related("items")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return SalesOrderWriteSerializer
        return SalesOrderSerializer

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Confirm a draft sales order."""
        order = self.get_object()
        if order.status != "draft":
            return Response(
                {"detail": "Only draft orders can be confirmed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = "confirmed"
        order.save()
        return Response(SalesOrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        """Mark order as shipped."""
        order = self.get_object()
        if order.status not in ("confirmed", "processing"):
            return Response(
                {"detail": "Order must be confirmed to ship."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = "shipped"
        order.save()
        return Response(SalesOrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def deliver(self, request, pk=None):
        """Mark order as delivered."""
        order = self.get_object()
        if order.status != "shipped":
            return Response(
                {"detail": "Order must be shipped to mark as delivered."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = "delivered"
        order.actual_delivery_date = timezone.now().date()
        order.save()
        return Response(SalesOrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def record_payment(self, request, pk=None):
        """Record a payment for a sales order."""
        order = self.get_object()
        amount = request.data.get("amount")
        if not amount:
            return Response(
                {"detail": "Amount is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.amount_paid += amount
        if order.amount_paid >= order.total_amount:
            order.payment_status = "paid"
        else:
            order.payment_status = "partial"
        order.save()
        return Response(SalesOrderSerializer(order).data)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Sales dashboard data."""
        qs = self.get_queryset()
        today = timezone.now().date()
        month_start = today.replace(day=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        monthly_revenue = qs.filter(
            order_date__gte=month_start,
            status__in=["confirmed", "processing", "shipped", "delivered"],
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

        prev_monthly_revenue = qs.filter(
            order_date__gte=prev_month_start,
            order_date__lt=month_start,
            status__in=["confirmed", "processing", "shipped", "delivered"],
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

        return Response({
            "monthly_revenue": monthly_revenue,
            "previous_monthly_revenue": prev_monthly_revenue,
            "revenue_growth": (
                round(
                    float((monthly_revenue - prev_monthly_revenue)
                          / prev_monthly_revenue * 100), 1
                ) if prev_monthly_revenue > 0 else 0
            ),
            "total_orders_this_month": qs.filter(
                order_date__gte=month_start,
            ).count(),
            "average_order_value": qs.filter(
                order_date__gte=month_start,
            ).aggregate(avg=Avg("total_amount"))["avg"] or 0,
            "by_status": list(
                qs.values("status")
                .annotate(count=Count("id"), total=Sum("total_amount"))
                .order_by("-count")
            ),
            "top_customers": list(
                qs.filter(status="delivered")
                .values("customer__name")
                .annotate(
                    order_count=Count("id"),
                    total_revenue=Sum("total_amount"),
                )
                .order_by("-total_revenue")[:5]
            ),
            "pending_payments": qs.filter(
                payment_status__in=["unpaid", "partial"]
            ).aggregate(total=Sum("total_amount"))["total"] or 0,
        })


class SalesReportViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for sales reports."""

    serializer_class = SalesReportSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "sales"
    filterset_fields = ["report_type"]
    ordering_fields = ["period_start"]

    def get_queryset(self):
        return SalesReport.objects.filter(
            organization=self.request.user.organization
        )
