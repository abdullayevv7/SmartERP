"""
Finance models: Account, Transaction, Invoice, Budget, Expense.
Double-entry bookkeeping system.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import Organization


class Account(models.Model):
    """Chart of accounts for double-entry bookkeeping."""

    ACCOUNT_TYPE_CHOICES = [
        ("asset", "Asset"),
        ("liability", "Liability"),
        ("equity", "Equity"),
        ("revenue", "Revenue"),
        ("expense", "Expense"),
    ]

    NORMAL_BALANCE_CHOICES = [
        ("debit", "Debit"),
        ("credit", "Credit"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="accounts"
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    normal_balance = models.CharField(max_length=10, choices=NORMAL_BALANCE_CHOICES)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_system_account = models.BooleanField(
        default=False, help_text="System accounts cannot be deleted."
    )
    current_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        unique_together = ["organization", "code"]
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self):
        return f"{self.code} - {self.name}"

    def recalculate_balance(self):
        """Recalculate balance from all transaction entries."""
        debits = self.debit_entries.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")
        credits = self.credit_entries.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")

        if self.normal_balance == "debit":
            self.current_balance = debits - credits
        else:
            self.current_balance = credits - debits

        self.save(update_fields=["current_balance"])
        return self.current_balance


class Transaction(models.Model):
    """Financial transaction with double-entry journal entries."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("posted", "Posted"),
        ("voided", "Voided"),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ("journal", "Journal Entry"),
        ("invoice", "Invoice"),
        ("payment", "Payment"),
        ("receipt", "Receipt"),
        ("expense", "Expense"),
        ("transfer", "Transfer"),
        ("adjustment", "Adjustment"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="transactions"
    )
    reference = models.CharField(max_length=50)
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPE_CHOICES, default="journal"
    )
    date = models.DateField()
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    related_invoice = models.ForeignKey(
        "Invoice", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transactions",
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_transactions",
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="finance/transactions/", blank=True, null=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        unique_together = ["organization", "reference"]

    def __str__(self):
        return f"{self.reference} - {self.description[:50]}"

    def post(self, user):
        """Post the transaction and update account balances."""
        if self.status != "draft":
            raise ValueError("Only draft transactions can be posted.")

        entries = self.entries.all()
        if not entries.exists():
            raise ValueError("Transaction must have at least one entry.")

        total_debits = entries.filter(entry_type="debit").aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")
        total_credits = entries.filter(entry_type="credit").aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")

        if total_debits != total_credits:
            raise ValueError(
                f"Debits ({total_debits}) must equal credits ({total_credits})."
            )

        self.status = "posted"
        self.posted_by = user
        self.posted_at = timezone.now()
        self.total_amount = total_debits
        self.save()

        # Update account balances
        for entry in entries:
            entry.account.recalculate_balance()

    def void(self, user):
        """Void a posted transaction."""
        if self.status != "posted":
            raise ValueError("Only posted transactions can be voided.")

        self.status = "voided"
        self.save()

        for entry in self.entries.all():
            entry.account.recalculate_balance()


class TransactionEntry(models.Model):
    """Individual debit/credit entry within a transaction."""

    ENTRY_TYPE_CHOICES = [
        ("debit", "Debit"),
        ("credit", "Credit"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="entries"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="%(class)s_entries",
    )
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.CharField(max_length=500, blank=True)

    # Polymorphic related_name based on entry type
    class Meta:
        verbose_name = "Transaction Entry"
        verbose_name_plural = "Transaction Entries"

    def __str__(self):
        return f"{self.entry_type}: {self.account.code} - {self.amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Set the reverse relation for account balance calculation
        if self.entry_type == "debit":
            Account.debit_entries = self.account.transactionentry_entries.filter(
                entry_type="debit"
            )
        elif self.entry_type == "credit":
            Account.credit_entries = self.account.transactionentry_entries.filter(
                entry_type="credit"
            )


class Invoice(models.Model):
    """Sales or purchase invoices."""

    INVOICE_TYPE_CHOICES = [
        ("sales", "Sales Invoice"),
        ("purchase", "Purchase Invoice"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("partial", "Partially Paid"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="invoices"
    )
    invoice_number = models.CharField(max_length=50)
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    # Customer/Supplier reference
    contact_name = models.CharField(max_length=200)
    contact_email = models.EmailField(blank=True)
    contact_address = models.TextField(blank=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Tax rate as percentage",
    )
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_due = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date"]
        unique_together = ["organization", "invoice_number"]

    def __str__(self):
        return f"{self.invoice_number} - {self.contact_name}"

    def calculate_totals(self):
        """Recalculate invoice totals from line items."""
        self.subtotal = self.line_items.aggregate(
            total=models.Sum("total")
        )["total"] or Decimal("0")
        self.tax_amount = self.subtotal * (self.tax_rate / Decimal("100"))
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.amount_due = self.total_amount - self.amount_paid
        self.save(update_fields=[
            "subtotal", "tax_amount", "total_amount", "amount_due",
        ])

    def record_payment(self, amount):
        """Record a payment against this invoice."""
        self.amount_paid += Decimal(str(amount))
        self.amount_due = self.total_amount - self.amount_paid
        if self.amount_due <= 0:
            self.status = "paid"
            self.amount_due = Decimal("0")
        else:
            self.status = "partial"
        self.save(update_fields=["amount_paid", "amount_due", "status"])


class InvoiceLineItem(models.Model):
    """Line items on an invoice."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="line_items"
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Revenue/expense account for this line item",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Budget(models.Model):
    """Budget planning and tracking."""

    PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annual", "Annual"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="budgets"
    )
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.CASCADE,
        related_name="budgets",
        null=True,
        blank=True,
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="budgets",
        null=True, blank=True,
    )
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    allocated_amount = models.DecimalField(max_digits=15, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_budgets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    @property
    def remaining_amount(self):
        return self.allocated_amount - self.spent_amount

    @property
    def utilization_percentage(self):
        if self.allocated_amount <= 0:
            return 0
        return round(
            (self.spent_amount / self.allocated_amount) * 100, 2
        )

    @property
    def is_over_budget(self):
        return self.spent_amount > self.allocated_amount


class Expense(models.Model):
    """Employee expense claims and tracking."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("reimbursed", "Reimbursed"),
    ]

    CATEGORY_CHOICES = [
        ("travel", "Travel"),
        ("meals", "Meals"),
        ("supplies", "Office Supplies"),
        ("equipment", "Equipment"),
        ("software", "Software"),
        ("training", "Training"),
        ("entertainment", "Entertainment"),
        ("utilities", "Utilities"),
        ("rent", "Rent"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="expenses"
    )
    reference = models.CharField(max_length=50)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_expenses",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    date = models.DateField()
    receipt = models.FileField(
        upload_to="finance/receipts/", blank=True, null=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
    )
    budget = models.ForeignKey(
        Budget, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="expenses",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_expenses",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        unique_together = ["organization", "reference"]

    def __str__(self):
        return f"{self.reference} - {self.category} ({self.amount})"
