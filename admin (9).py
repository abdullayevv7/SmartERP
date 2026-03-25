"""
Finance serializers for accounts, transactions, invoices, budgets, and expenses.
"""

from decimal import Decimal

from rest_framework import serializers

from .models import (
    Account,
    Budget,
    Expense,
    Invoice,
    InvoiceLineItem,
    Transaction,
    TransactionEntry,
)


class AccountSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Account
        fields = [
            "id", "code", "name", "account_type", "normal_balance",
            "parent", "parent_name", "description", "is_active",
            "is_system_account", "current_balance",
            "children", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "is_system_account", "current_balance",
            "created_at", "updated_at",
        ]

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return AccountSerializer(children, many=True).data

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        return Account.objects.create(organization=organization, **validated_data)


class TransactionEntrySerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    account_code = serializers.CharField(source="account.code", read_only=True)

    class Meta:
        model = TransactionEntry
        fields = [
            "id", "account", "account_name", "account_code",
            "entry_type", "amount", "description",
        ]
        read_only_fields = ["id"]


class TransactionSerializer(serializers.ModelSerializer):
    entries = TransactionEntrySerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True
    )
    posted_by_name = serializers.CharField(
        source="posted_by.full_name", read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            "id", "reference", "transaction_type", "date",
            "description", "status", "total_amount", "currency",
            "related_invoice", "posted_by", "posted_by_name",
            "posted_at", "notes", "attachment",
            "created_by", "created_by_name",
            "entries", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "total_amount", "posted_by",
            "posted_at", "created_by", "created_at", "updated_at",
        ]


class TransactionWriteSerializer(serializers.ModelSerializer):
    entries = TransactionEntrySerializer(many=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "reference", "transaction_type", "date",
            "description", "currency", "related_invoice",
            "notes", "attachment", "entries",
        ]
        read_only_fields = ["id"]

    def validate_entries(self, entries):
        if len(entries) < 2:
            raise serializers.ValidationError(
                "A transaction must have at least 2 entries."
            )

        total_debits = sum(
            e["amount"] for e in entries if e["entry_type"] == "debit"
        )
        total_credits = sum(
            e["amount"] for e in entries if e["entry_type"] == "credit"
        )

        if total_debits != total_credits:
            raise serializers.ValidationError(
                f"Total debits ({total_debits}) must equal total credits ({total_credits})."
            )

        return entries

    def create(self, validated_data):
        entries_data = validated_data.pop("entries")
        organization = self.context["request"].user.organization
        user = self.context["request"].user

        transaction = Transaction.objects.create(
            organization=organization,
            created_by=user,
            total_amount=sum(
                e["amount"] for e in entries_data if e["entry_type"] == "debit"
            ),
            **validated_data,
        )

        for entry_data in entries_data:
            TransactionEntry.objects.create(
                transaction=transaction, **entry_data
            )

        return transaction

    def update(self, instance, validated_data):
        if instance.status != "draft":
            raise serializers.ValidationError(
                "Only draft transactions can be modified."
            )

        entries_data = validated_data.pop("entries", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if entries_data is not None:
            instance.entries.all().delete()
            for entry_data in entries_data:
                TransactionEntry.objects.create(
                    transaction=instance, **entry_data
                )
            instance.total_amount = sum(
                e["amount"] for e in entries_data if e["entry_type"] == "debit"
            )
            instance.save(update_fields=["total_amount"])

        return instance


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = [
            "id", "description", "quantity", "unit_price",
            "total", "account",
        ]
        read_only_fields = ["id", "total"]


class InvoiceSerializer(serializers.ModelSerializer):
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "invoice_type", "status",
            "contact_name", "contact_email", "contact_address",
            "issue_date", "due_date",
            "subtotal", "tax_rate", "tax_amount",
            "discount_amount", "total_amount",
            "amount_paid", "amount_due", "currency",
            "notes", "terms",
            "created_by", "created_by_name",
            "line_items", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "subtotal", "tax_amount", "total_amount",
            "amount_due", "created_by", "created_at", "updated_at",
        ]


class InvoiceWriteSerializer(serializers.ModelSerializer):
    line_items = InvoiceLineItemSerializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "invoice_type",
            "contact_name", "contact_email", "contact_address",
            "issue_date", "due_date",
            "tax_rate", "discount_amount", "currency",
            "notes", "terms", "line_items",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        line_items_data = validated_data.pop("line_items")
        organization = self.context["request"].user.organization
        user = self.context["request"].user

        invoice = Invoice.objects.create(
            organization=organization,
            created_by=user,
            **validated_data,
        )

        for item_data in line_items_data:
            InvoiceLineItem.objects.create(invoice=invoice, **item_data)

        invoice.calculate_totals()
        return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop("line_items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if line_items_data is not None:
            instance.line_items.all().delete()
            for item_data in line_items_data:
                InvoiceLineItem.objects.create(invoice=instance, **item_data)
            instance.calculate_totals()

        return instance


class BudgetSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.ReadOnlyField()
    utilization_percentage = serializers.ReadOnlyField()
    is_over_budget = serializers.ReadOnlyField()
    department_name = serializers.CharField(
        source="department.name", read_only=True
    )
    account_name = serializers.CharField(source="account.name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True
    )

    class Meta:
        model = Budget
        fields = [
            "id", "name", "department", "department_name",
            "account", "account_name",
            "period_type", "start_date", "end_date",
            "allocated_amount", "spent_amount",
            "remaining_amount", "utilization_percentage",
            "is_over_budget", "status", "notes",
            "created_by", "created_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "spent_amount", "created_by",
            "created_at", "updated_at",
        ]

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        user = self.context["request"].user
        return Budget.objects.create(
            organization=organization,
            created_by=user,
            **validated_data,
        )


class ExpenseSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.CharField(
        source="submitted_by.full_name", read_only=True
    )
    approved_by_name = serializers.CharField(
        source="approved_by.full_name", read_only=True
    )

    class Meta:
        model = Expense
        fields = [
            "id", "reference", "submitted_by", "submitted_by_name",
            "category", "description", "amount", "currency",
            "date", "receipt", "status",
            "account", "budget",
            "approved_by", "approved_by_name",
            "approved_at", "rejection_reason", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "submitted_by", "approved_by", "approved_at",
            "rejection_reason", "created_at", "updated_at",
        ]

    def create(self, validated_data):
        organization = self.context["request"].user.organization
        user = self.context["request"].user
        return Expense.objects.create(
            organization=organization,
            submitted_by=user,
            **validated_data,
        )
