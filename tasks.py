"""
Finance views for accounts, transactions, invoices, budgets, and expenses.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasApprovalPermission, HasModulePermission
from utils.mixins import TenantQuerySetMixin

from .models import Account, Budget, Expense, Invoice, Transaction
from .serializers import (
    AccountSerializer,
    BudgetSerializer,
    ExpenseSerializer,
    InvoiceSerializer,
    InvoiceWriteSerializer,
    TransactionSerializer,
    TransactionWriteSerializer,
)
from .services import FinancialReportService


class AccountViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for chart of accounts."""

    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "finance"
    filterset_fields = ["account_type", "is_active", "parent"]
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "current_balance"]

    def get_queryset(self):
        return Account.objects.filter(
            organization=self.request.user.organization
        ).select_related("parent")

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Return accounts as a hierarchical tree."""
        accounts = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def trial_balance(self, request):
        """Generate trial balance report."""
        accounts = self.get_queryset().filter(
            is_active=True, current_balance__gt=0
        ).values("code", "name", "account_type", "normal_balance", "current_balance")

        total_debits = Decimal("0")
        total_credits = Decimal("0")

        for acc in accounts:
            if acc["normal_balance"] == "debit":
                total_debits += acc["current_balance"]
            else:
                total_credits += acc["current_balance"]

        return Response({
            "accounts": list(accounts),
            "total_debits": total_debits,
            "total_credits": total_credits,
            "is_balanced": total_debits == total_credits,
        })

    def destroy(self, request, *args, **kwargs):
        account = self.get_object()
        if account.is_system_account:
            return Response(
                {"detail": "System accounts cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if account.current_balance != 0:
            return Response(
                {"detail": "Cannot delete account with non-zero balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class TransactionViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for financial transactions."""

    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "finance"
    filterset_fields = ["transaction_type", "status", "date"]
    search_fields = ["reference", "description"]
    ordering_fields = ["date", "total_amount", "created_at"]

    def get_queryset(self):
        return Transaction.objects.filter(
            organization=self.request.user.organization
        ).select_related("created_by", "posted_by").prefetch_related("entries__account")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return TransactionWriteSerializer
        return TransactionSerializer

    @action(detail=True, methods=["post"])
    def post_transaction(self, request, pk=None):
        """Post a draft transaction."""
        transaction = self.get_object()
        try:
            transaction.post(request.user)
            return Response(
                TransactionSerializer(transaction).data,
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        """Void a posted transaction."""
        transaction = self.get_object()
        try:
            transaction.void(request.user)
            return Response(
                TransactionSerializer(transaction).data,
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class InvoiceViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for invoices."""

    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "finance"
    filterset_fields = ["invoice_type", "status"]
    search_fields = ["invoice_number", "contact_name"]
    ordering_fields = ["issue_date", "due_date", "total_amount"]

    def get_queryset(self):
        return Invoice.objects.filter(
            organization=self.request.user.organization
        ).select_related("created_by").prefetch_related("line_items")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return InvoiceWriteSerializer
        return InvoiceSerializer

    @action(detail=True, methods=["post"])
    def record_payment(self, request, pk=None):
        """Record a payment against an invoice."""
        invoice = self.get_object()
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

        if amount <= 0:
            return Response(
                {"detail": "Amount must be positive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.record_payment(amount)
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        """List overdue invoices."""
        invoices = self.get_queryset().filter(
            status__in=["sent", "partial"],
            due_date__lt=timezone.now().date(),
        )
        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Invoice summary statistics."""
        qs = self.get_queryset()
        return Response({
            "total_invoices": qs.count(),
            "total_receivable": qs.filter(
                invoice_type="sales", status__in=["sent", "partial"]
            ).aggregate(total=Sum("amount_due"))["total"] or 0,
            "total_payable": qs.filter(
                invoice_type="purchase", status__in=["sent", "partial"]
            ).aggregate(total=Sum("amount_due"))["total"] or 0,
            "overdue_count": qs.filter(
                status__in=["sent", "partial"],
                due_date__lt=timezone.now().date(),
            ).count(),
        })


class BudgetViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for budgets."""

    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "finance"
    filterset_fields = ["department", "period_type", "status"]
    search_fields = ["name"]
    ordering_fields = ["start_date", "allocated_amount"]

    def get_queryset(self):
        return Budget.objects.filter(
            organization=self.request.user.organization
        ).select_related("department", "account", "created_by")

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """Budget utilization overview."""
        budgets = self.get_queryset().filter(status="active")
        data = []
        for budget in budgets:
            data.append({
                "id": budget.id,
                "name": budget.name,
                "allocated": budget.allocated_amount,
                "spent": budget.spent_amount,
                "remaining": budget.remaining_amount,
                "utilization": budget.utilization_percentage,
                "is_over_budget": budget.is_over_budget,
            })
        return Response(data)


class ExpenseViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD operations for expense claims."""

    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, HasModulePermission]
    module_name = "finance"
    filterset_fields = ["category", "status", "submitted_by"]
    search_fields = ["reference", "description"]
    ordering_fields = ["date", "amount", "created_at"]

    def get_queryset(self):
        qs = Expense.objects.filter(
            organization=self.request.user.organization
        ).select_related("submitted_by", "approved_by")

        user = self.request.user
        if not user.is_org_admin and not user.is_superuser:
            qs = qs.filter(submitted_by=user)

        return qs

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve an expense claim."""
        expense = self.get_object()
        if expense.status != "submitted":
            return Response(
                {"detail": "Only submitted expenses can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expense.status = "approved"
        expense.approved_by = request.user
        expense.approved_at = timezone.now()
        expense.save()

        # Update budget spent amount if linked
        if expense.budget:
            expense.budget.spent_amount += expense.amount
            expense.budget.save(update_fields=["spent_amount"])

        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject an expense claim."""
        expense = self.get_object()
        if expense.status != "submitted":
            return Response(
                {"detail": "Only submitted expenses can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expense.status = "rejected"
        expense.approved_by = request.user
        expense.approved_at = timezone.now()
        expense.rejection_reason = request.data.get("reason", "")
        expense.save()
        return Response(ExpenseSerializer(expense).data)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Finance dashboard data."""
        service = FinancialReportService(request.user.organization)
        return Response(service.get_dashboard_data())
