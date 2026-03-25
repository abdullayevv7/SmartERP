"""
Finance services for complex business logic and reporting.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import Account, Budget, Expense, Invoice, Transaction


class FinancialReportService:
    """Service class for generating financial reports and dashboard data."""

    def __init__(self, organization):
        self.organization = organization

    def get_dashboard_data(self):
        """Compile all dashboard metrics."""
        return {
            "revenue": self._get_revenue_summary(),
            "expenses": self._get_expense_summary(),
            "cash_flow": self._get_cash_flow(),
            "accounts_receivable": self._get_accounts_receivable(),
            "accounts_payable": self._get_accounts_payable(),
            "budget_overview": self._get_budget_overview(),
            "recent_transactions": self._get_recent_transactions(),
            "monthly_trend": self._get_monthly_trend(),
        }

    def _get_revenue_summary(self):
        """Calculate revenue for current month and comparison."""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        current_revenue = Invoice.objects.filter(
            organization=self.organization,
            invoice_type="sales",
            status__in=["paid", "partial"],
            issue_date__gte=month_start,
        ).aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")

        prev_revenue = Invoice.objects.filter(
            organization=self.organization,
            invoice_type="sales",
            status__in=["paid", "partial"],
            issue_date__gte=prev_month_start,
            issue_date__lt=month_start,
        ).aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")

        change_pct = Decimal("0")
        if prev_revenue > 0:
            change_pct = ((current_revenue - prev_revenue) / prev_revenue * 100).quantize(
                Decimal("0.01")
            )

        return {
            "current_month": current_revenue,
            "previous_month": prev_revenue,
            "change_percentage": change_pct,
        }

    def _get_expense_summary(self):
        """Calculate expense totals by category."""
        today = timezone.now().date()
        month_start = today.replace(day=1)

        expenses = Expense.objects.filter(
            organization=self.organization,
            status__in=["approved", "reimbursed"],
            date__gte=month_start,
        )

        total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        by_category = list(
            expenses.values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        return {
            "total": total,
            "by_category": by_category,
        }

    def _get_cash_flow(self):
        """Calculate cash inflows and outflows."""
        today = timezone.now().date()
        month_start = today.replace(day=1)

        inflows = Transaction.objects.filter(
            organization=self.organization,
            status="posted",
            transaction_type__in=["receipt", "payment"],
            date__gte=month_start,
        ).filter(
            entries__entry_type="debit",
            entries__account__account_type="asset",
        ).aggregate(total=Sum("entries__amount"))["total"] or Decimal("0")

        outflows = Transaction.objects.filter(
            organization=self.organization,
            status="posted",
            transaction_type__in=["expense", "payment"],
            date__gte=month_start,
        ).filter(
            entries__entry_type="credit",
            entries__account__account_type="asset",
        ).aggregate(total=Sum("entries__amount"))["total"] or Decimal("0")

        return {
            "inflows": inflows,
            "outflows": outflows,
            "net": inflows - outflows,
        }

    def _get_accounts_receivable(self):
        """Get outstanding accounts receivable."""
        today = timezone.now().date()
        invoices = Invoice.objects.filter(
            organization=self.organization,
            invoice_type="sales",
            status__in=["sent", "partial"],
        )

        total = invoices.aggregate(total=Sum("amount_due"))["total"] or Decimal("0")
        overdue = invoices.filter(due_date__lt=today).aggregate(
            total=Sum("amount_due")
        )["total"] or Decimal("0")

        return {
            "total": total,
            "overdue": overdue,
            "count": invoices.count(),
        }

    def _get_accounts_payable(self):
        """Get outstanding accounts payable."""
        today = timezone.now().date()
        invoices = Invoice.objects.filter(
            organization=self.organization,
            invoice_type="purchase",
            status__in=["sent", "partial"],
        )

        total = invoices.aggregate(total=Sum("amount_due"))["total"] or Decimal("0")
        overdue = invoices.filter(due_date__lt=today).aggregate(
            total=Sum("amount_due")
        )["total"] or Decimal("0")

        return {
            "total": total,
            "overdue": overdue,
            "count": invoices.count(),
        }

    def _get_budget_overview(self):
        """Get active budget utilization summary."""
        budgets = Budget.objects.filter(
            organization=self.organization,
            status="active",
        )

        total_allocated = budgets.aggregate(
            total=Sum("allocated_amount")
        )["total"] or Decimal("0")
        total_spent = budgets.aggregate(
            total=Sum("spent_amount")
        )["total"] or Decimal("0")

        over_budget_count = 0
        for budget in budgets:
            if budget.is_over_budget:
                over_budget_count += 1

        return {
            "total_allocated": total_allocated,
            "total_spent": total_spent,
            "remaining": total_allocated - total_spent,
            "over_budget_count": over_budget_count,
            "active_budgets": budgets.count(),
        }

    def _get_recent_transactions(self):
        """Get the most recent posted transactions."""
        transactions = Transaction.objects.filter(
            organization=self.organization,
            status="posted",
        ).order_by("-date", "-created_at")[:10]

        return [
            {
                "id": str(t.id),
                "reference": t.reference,
                "type": t.transaction_type,
                "date": t.date.isoformat(),
                "description": t.description[:100],
                "amount": t.total_amount,
            }
            for t in transactions
        ]

    def _get_monthly_trend(self):
        """Get 12-month revenue and expense trend."""
        today = timezone.now().date()
        months = []

        for i in range(11, -1, -1):
            month_date = today - timedelta(days=i * 30)
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                next_month_start = month_start.replace(year=month_date.year + 1, month=1)
            else:
                next_month_start = month_start.replace(month=month_date.month + 1)

            revenue = Invoice.objects.filter(
                organization=self.organization,
                invoice_type="sales",
                status__in=["paid", "partial"],
                issue_date__gte=month_start,
                issue_date__lt=next_month_start,
            ).aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")

            expenses = Expense.objects.filter(
                organization=self.organization,
                status__in=["approved", "reimbursed"],
                date__gte=month_start,
                date__lt=next_month_start,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            months.append({
                "month": month_start.strftime("%Y-%m"),
                "revenue": revenue,
                "expenses": expenses,
                "profit": revenue - expenses,
            })

        return months

    def generate_profit_loss(self, start_date, end_date):
        """Generate profit and loss statement for a period."""
        revenue_accounts = Account.objects.filter(
            organization=self.organization,
            account_type="revenue",
            is_active=True,
        )

        expense_accounts = Account.objects.filter(
            organization=self.organization,
            account_type="expense",
            is_active=True,
        )

        total_revenue = sum(acc.current_balance for acc in revenue_accounts)
        total_expenses = sum(acc.current_balance for acc in expense_accounts)

        return {
            "period": {"start": start_date, "end": end_date},
            "revenue": [
                {"code": acc.code, "name": acc.name, "balance": acc.current_balance}
                for acc in revenue_accounts
            ],
            "expenses": [
                {"code": acc.code, "name": acc.name, "balance": acc.current_balance}
                for acc in expense_accounts
            ],
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_income": total_revenue - total_expenses,
        }

    def generate_balance_sheet(self):
        """Generate a balance sheet."""
        assets = Account.objects.filter(
            organization=self.organization,
            account_type="asset",
            is_active=True,
        )
        liabilities = Account.objects.filter(
            organization=self.organization,
            account_type="liability",
            is_active=True,
        )
        equity = Account.objects.filter(
            organization=self.organization,
            account_type="equity",
            is_active=True,
        )

        total_assets = sum(acc.current_balance for acc in assets)
        total_liabilities = sum(acc.current_balance for acc in liabilities)
        total_equity = sum(acc.current_balance for acc in equity)

        return {
            "assets": [
                {"code": acc.code, "name": acc.name, "balance": acc.current_balance}
                for acc in assets
            ],
            "liabilities": [
                {"code": acc.code, "name": acc.name, "balance": acc.current_balance}
                for acc in liabilities
            ],
            "equity": [
                {"code": acc.code, "name": acc.name, "balance": acc.current_balance}
                for acc in equity
            ],
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "is_balanced": total_assets == (total_liabilities + total_equity),
        }
