"""
Finance URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    BudgetViewSet,
    ExpenseViewSet,
    InvoiceViewSet,
    TransactionViewSet,
)

router = DefaultRouter()
router.register(r"accounts", AccountViewSet, basename="account")
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"budgets", BudgetViewSet, basename="budget")
router.register(r"expenses", ExpenseViewSet, basename="expense")

urlpatterns = [
    path("", include(router.urls)),
]
