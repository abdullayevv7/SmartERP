"""
Procurement models: Supplier, PurchaseRequest, PurchaseOrder.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import Organization


class Supplier(models.Model):
    """Supplier/vendor management."""

    RATING_CHOICES = [
        (1, "Poor"),
        (2, "Below Average"),
        (3, "Average"),
        (4, "Good"),
        (5, "Excellent"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="suppliers"
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=300)
    contact_person = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(
        max_length=50, default="Net 30",
        help_text="e.g., Net 30, Net 60, COD",
    )
    currency = models.CharField(max_length=3, default="USD")
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES, default=3
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["organization", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def total_orders(self):
        return self.purchase_orders.count()

    @property
    def total_spend(self):
        return (
            self.purchase_orders.filter(status="received").aggregate(
                total=models.Sum("total_amount")
            )["total"]
            or Decimal("0")
        )


class PurchaseRequest(models.Model):
    """Internal purchase request before creating a purchase order."""

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("ordered", "Ordered"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="purchase_requests"
    )
    reference = models.CharField(max_length=50)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="purchase_requests",
    )
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        related_name="purchase_requests",
    )
    title = models.CharField(max_length=300)
    description = models.TextField()
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    estimated_cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    required_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_purchase_requests",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["organization", "reference"]

    def __str__(self):
        return f"{self.reference} - {self.title}"


class PurchaseRequestItem(models.Model):
    """Items in a purchase request."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_request = models.ForeignKey(
        PurchaseRequest, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=500)
    quantity = models.PositiveIntegerField(default=1)
    estimated_unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    estimated_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )

    def save(self, *args, **kwargs):
        self.estimated_total = self.quantity * self.estimated_unit_price
        super().save(*args, **kwargs)


class PurchaseOrder(models.Model):
    """Purchase order sent to suppliers."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent to Supplier"),
        ("confirmed", "Confirmed"),
        ("partially_received", "Partially Received"),
        ("received", "Fully Received"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="purchase_orders"
    )
    order_number = models.CharField(max_length=50)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="purchase_orders"
    )
    purchase_request = models.ForeignKey(
        PurchaseRequest, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="purchase_orders",
    )
    status = models.CharField(
        max_length=25, choices=STATUS_CHOICES, default="draft"
    )
    order_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    payment_terms = models.CharField(max_length=50, blank=True)
    shipping_address = models.TextField(blank=True)
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Destination warehouse for received goods",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_purchase_orders",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_purchase_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-order_date"]
        unique_together = ["organization", "order_number"]

    def __str__(self):
        return f"{self.order_number} - {self.supplier.name}"

    def calculate_totals(self):
        """Recalculate order totals from line items."""
        self.subtotal = self.items.aggregate(
            total=models.Sum("total")
        )["total"] or Decimal("0")
        self.total_amount = (
            self.subtotal + self.tax_amount
            + self.shipping_cost - self.discount_amount
        )
        self.save(update_fields=["subtotal", "total_amount"])


class PurchaseOrderItem(models.Model):
    """Line items on a purchase order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=500)
    quantity_ordered = models.PositiveIntegerField(default=1)
    quantity_received = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} x{self.quantity_ordered}"

    def save(self, *args, **kwargs):
        self.total = self.quantity_ordered * self.unit_price
        super().save(*args, **kwargs)

    @property
    def is_fully_received(self):
        return self.quantity_received >= self.quantity_ordered
