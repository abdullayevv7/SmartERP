"""
Inventory models: Warehouse, Product, StockMovement, StockLevel.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.accounts.models import Organization


class Warehouse(models.Model):
    """Physical warehouse or storage location."""

    WAREHOUSE_TYPE_CHOICES = [
        ("main", "Main Warehouse"),
        ("branch", "Branch Warehouse"),
        ("transit", "Transit Warehouse"),
        ("virtual", "Virtual Warehouse"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="warehouses"
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    warehouse_type = models.CharField(
        max_length=20, choices=WAREHOUSE_TYPE_CHOICES, default="main"
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_warehouses",
    )
    capacity = models.PositiveIntegerField(
        default=0, help_text="Maximum capacity in units"
    )
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["organization", "code"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def total_stock_value(self):
        return (
            self.stock_levels.aggregate(
                total=models.Sum(
                    models.F("quantity") * models.F("product__unit_cost"),
                    output_field=models.DecimalField(),
                )
            )["total"]
            or Decimal("0")
        )


class ProductCategory(models.Model):
    """Product categorization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="product_categories"
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["organization", "code"]
        verbose_name_plural = "Product Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product/item in the inventory system."""

    PRODUCT_TYPE_CHOICES = [
        ("goods", "Goods"),
        ("service", "Service"),
        ("consumable", "Consumable"),
        ("raw_material", "Raw Material"),
    ]

    UNIT_CHOICES = [
        ("pcs", "Pieces"),
        ("kg", "Kilograms"),
        ("g", "Grams"),
        ("l", "Liters"),
        ("ml", "Milliliters"),
        ("m", "Meters"),
        ("box", "Boxes"),
        ("set", "Sets"),
        ("unit", "Units"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="products"
    )
    sku = models.CharField(max_length=50, help_text="Stock Keeping Unit")
    barcode = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products",
    )
    product_type = models.CharField(
        max_length=20, choices=PRODUCT_TYPE_CHOICES, default="goods"
    )
    unit_of_measure = models.CharField(
        max_length=10, choices=UNIT_CHOICES, default="pcs"
    )
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    min_stock_level = models.PositiveIntegerField(
        default=0, help_text="Minimum stock level before reorder alert"
    )
    reorder_quantity = models.PositiveIntegerField(
        default=0, help_text="Default reorder quantity"
    )
    max_stock_level = models.PositiveIntegerField(
        default=0, help_text="Maximum stock level"
    )
    weight = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True,
        help_text="Weight in kg",
    )
    image = models.ImageField(
        upload_to="inventory/products/", blank=True, null=True
    )
    is_active = models.BooleanField(default=True)
    is_trackable = models.BooleanField(
        default=True, help_text="Track stock levels for this product"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["organization", "sku"]

    def __str__(self):
        return f"{self.sku} - {self.name}"

    @property
    def total_stock(self):
        """Total stock across all warehouses."""
        return (
            self.stock_levels.aggregate(total=models.Sum("quantity"))["total"]
            or 0
        )

    @property
    def is_low_stock(self):
        """Check if any warehouse has stock below minimum."""
        return self.total_stock <= self.min_stock_level

    @property
    def stock_value(self):
        """Total value of stock across all warehouses."""
        return Decimal(str(self.total_stock)) * self.unit_cost


class StockLevel(models.Model):
    """Current stock level of a product in a specific warehouse."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="stock_levels"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_levels"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="stock_levels"
    )
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(
        default=0, help_text="Quantity reserved for pending orders"
    )
    last_counted_at = models.DateTimeField(null=True, blank=True)
    last_movement_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["product", "warehouse"]
        ordering = ["product__name", "warehouse__name"]

    def __str__(self):
        return f"{self.product.sku} @ {self.warehouse.code}: {self.quantity}"

    @property
    def available_quantity(self):
        """Quantity available (not reserved)."""
        return max(0, self.quantity - self.reserved_quantity)


class StockMovement(models.Model):
    """Record of stock movements (inbound, outbound, transfers)."""

    MOVEMENT_TYPE_CHOICES = [
        ("inbound", "Inbound (Receipt)"),
        ("outbound", "Outbound (Dispatch)"),
        ("transfer", "Inter-Warehouse Transfer"),
        ("adjustment", "Stock Adjustment"),
        ("return", "Return"),
        ("scrap", "Scrap/Write-off"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_transit", "In Transit"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="stock_movements"
    )
    reference = models.CharField(max_length=50)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="movements"
    )
    source_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="outgoing_movements",
    )
    destination_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="incoming_movements",
    )
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    total_cost = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    reason = models.TextField(blank=True)
    related_purchase_order = models.CharField(max_length=50, blank=True)
    related_sales_order = models.CharField(max_length=50, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="stock_movements",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["organization", "reference"]

    def __str__(self):
        return f"{self.reference} - {self.movement_type}: {self.product.sku} x{self.quantity}"

    def save(self, *args, **kwargs):
        if self.unit_cost and self.quantity:
            self.total_cost = self.unit_cost * self.quantity
        super().save(*args, **kwargs)

    def complete(self, user):
        """Complete the movement and update stock levels."""
        from django.utils import timezone

        if self.status != "pending" and self.status != "in_transit":
            raise ValueError("Only pending/in-transit movements can be completed.")

        # Update source warehouse stock
        if self.source_warehouse:
            stock, _ = StockLevel.objects.get_or_create(
                organization=self.organization,
                product=self.product,
                warehouse=self.source_warehouse,
            )
            stock.quantity -= self.quantity
            stock.last_movement_at = timezone.now()
            stock.save()

        # Update destination warehouse stock
        if self.destination_warehouse:
            stock, _ = StockLevel.objects.get_or_create(
                organization=self.organization,
                product=self.product,
                warehouse=self.destination_warehouse,
            )
            stock.quantity += self.quantity
            stock.last_movement_at = timezone.now()
            stock.save()

        self.status = "completed"
        self.performed_by = user
        self.completed_at = timezone.now()
        self.save()
