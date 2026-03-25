"""
Sales models: Customer, Quotation, SalesOrder, SalesReport.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.accounts.models import Organization


class Customer(models.Model):
    """Customer management."""

    CUSTOMER_TYPE_CHOICES = [
        ("individual", "Individual"),
        ("company", "Company"),
        ("government", "Government"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="customers"
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=300)
    customer_type = models.CharField(
        max_length=20, choices=CUSTOMER_TYPE_CHOICES, default="company"
    )
    contact_person = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    credit_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    payment_terms = models.CharField(max_length=50, default="Net 30")
    currency = models.CharField(max_length=3, default="USD")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_customers",
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
    def total_revenue(self):
        return (
            self.sales_orders.filter(status="delivered").aggregate(
                total=models.Sum("total_amount")
            )["total"]
            or Decimal("0")
        )

    @property
    def outstanding_balance(self):
        return (
            self.sales_orders.filter(
                status__in=["confirmed", "shipped"]
            ).aggregate(total=models.Sum("total_amount"))["total"]
            or Decimal("0")
        )


class Quotation(models.Model):
    """Sales quotation/proposal."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="quotations"
    )
    quotation_number = models.CharField(max_length=50)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="quotations"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    issue_date = models.DateField()
    valid_until = models.DateField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    terms = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_quotations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date"]
        unique_together = ["organization", "quotation_number"]

    def __str__(self):
        return f"{self.quotation_number} - {self.customer.name}"

    def calculate_totals(self):
        self.subtotal = self.items.aggregate(
            total=models.Sum("total")
        )["total"] or Decimal("0")
        self.tax_amount = self.subtotal * (self.tax_rate / Decimal("100"))
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.save(update_fields=["subtotal", "tax_amount", "total_amount"])


class QuotationItem(models.Model):
    """Line items on a quotation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(
        Quotation, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class SalesOrder(models.Model):
    """Sales order processing."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("partial", "Partially Paid"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="sales_orders"
    )
    order_number = models.CharField(max_length=50)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="sales_orders"
    )
    quotation = models.ForeignKey(
        Quotation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_orders",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid"
    )
    order_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    shipping_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Source warehouse for fulfillment",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_sales_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-order_date"]
        unique_together = ["organization", "order_number"]

    def __str__(self):
        return f"{self.order_number} - {self.customer.name}"

    def calculate_totals(self):
        self.subtotal = self.items.aggregate(
            total=models.Sum("total")
        )["total"] or Decimal("0")
        self.tax_amount = self.subtotal * (self.tax_rate / Decimal("100"))
        self.total_amount = (
            self.subtotal + self.tax_amount
            + self.shipping_cost - self.discount_amount
        )
        self.save(update_fields=[
            "subtotal", "tax_amount", "total_amount",
        ])


class SalesOrderItem(models.Model):
    """Line items on a sales order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sales_order = models.ForeignKey(
        SalesOrder, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class SalesReport(models.Model):
    """Pre-computed sales reports for analytics."""

    REPORT_TYPE_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annual", "Annual"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="sales_reports"
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    total_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gross_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    new_customers = models.PositiveIntegerField(default=0)
    returning_customers = models.PositiveIntegerField(default=0)
    average_order_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    top_products = models.JSONField(default=list)
    top_customers = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_start"]
        unique_together = ["organization", "report_type", "period_start"]

    def __str__(self):
        return f"{self.report_type} Report: {self.period_start} - {self.period_end}"
