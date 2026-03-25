"""
Finance admin configuration.
"""

from django.contrib import admin

from .models import (
    Account,
    Budget,
    Expense,
    Invoice,
    InvoiceLineItem,
    Transaction,
    TransactionEntry,
)


class TransactionEntryInline(admin.TabularInline):
    model = TransactionEntry
    extra = 2


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 1


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [
        "code", "name", "account_type", "normal_balance",
        "current_balance", "is_active", "organization",
    ]
    list_filter = ["organization", "account_type", "is_active"]
    search_fields = ["code", "name"]
    readonly_fields = ["current_balance", "created_at", "updated_at"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "reference", "transaction_type", "date", "description",
        "total_amount", "status", "organization",
    ]
    list_filter = ["organization", "transaction_type", "status"]
    search_fields = ["reference", "description"]
    inlines = [TransactionEntryInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number", "invoice_type", "contact_name",
        "total_amount", "amount_due", "status", "due_date",
    ]
    list_filter = ["organization", "invoice_type", "status"]
    search_fields = ["invoice_number", "contact_name"]
    inlines = [InvoiceLineItemInline]
    readonly_fields = ["subtotal", "tax_amount", "total_amount", "amount_due"]


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = [
        "name", "department", "period_type", "allocated_amount",
        "spent_amount", "status", "organization",
    ]
    list_filter = ["organization", "period_type", "status"]
    search_fields = ["name"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        "reference", "submitted_by", "category", "amount",
        "status", "date", "organization",
    ]
    list_filter = ["organization", "category", "status"]
    search_fields = ["reference", "description"]
