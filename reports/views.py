import csv
from collections import defaultdict
from datetime import timedelta

from common.date_ranges import resolve_date_range
from django.db.models import Count, Sum
from django.http import HttpResponse
from expenses.models import Expense
from invoices.models import Invoice, Payment
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from teams.models import Membership
from teams.services import get_active_team
from common.plan_gating import business_plan_required_response


def _staff_forbidden(request, team):
    """
    Reports are aggregate whole-business financial data — same
    category already hidden from Staff on Overview and Settings.
    Unlike those, this is enforced here on the backend too, not just
    hidden in the UI.
    """
    membership = Membership.objects.filter(team=team, user=request.user).first()
    if membership and membership.role == Membership.Role.STAFF:
        return Response({"message": "Reports aren't available to staff accounts."}, status=status.HTTP_403_FORBIDDEN)
    return None


def _access_forbidden(request, team):
    staff_check = _staff_forbidden(request, team)
    if staff_check:
        return staff_check
    if not team or team.plan != "business":
        return business_plan_required_response("Reports")
    return None

def _bucket_key(d, granularity):
    if granularity == "day":
        return d.isoformat()
    if granularity == "week":
        start = d - timedelta(days=d.weekday())
        return start.isoformat()
    return d.replace(day=1).isoformat()


def _choose_granularity(date_from, date_to):
    """
    Auto-picks a chart bucket size from how wide the selected range
    is — daily for up to 2 weeks, weekly up to ~4 months, monthly
    beyond that — so the chart stays readable without the person
    having to choose a granularity themselves.
    """
    if not date_from or not date_to:
        return "month"
    span_days = (date_to - date_from).days
    if span_days <= 14:
        return "day"
    if span_days <= 120:
        return "week"
    return "month"


class ReportSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        forbidden = _access_forbidden(request, team)
        if forbidden:
            return forbidden

        date_from, date_to = resolve_date_range(request)

        payments = Payment.objects.filter(invoice__team=team)
        expenses = Expense.objects.filter(team=team)
        invoices = Invoice.objects.filter(team=team)
        if date_from:
            payments = payments.filter(recorded_at__date__gte=date_from)
            expenses = expenses.filter(expense_date__gte=date_from)
            invoices = invoices.filter(recorded_at__date__gte=date_from)
        if date_to:
            payments = payments.filter(recorded_at__date__lte=date_to)
            expenses = expenses.filter(expense_date__lte=date_to)
            invoices = invoices.filter(recorded_at__date__lte=date_to)

        total_sales = payments.aggregate(s=Sum("amount"))["s"] or 0
        total_expenses = expenses.aggregate(s=Sum("amount"))["s"] or 0

        return Response(
            {
                "total_sales": float(total_sales),
                "total_expenses": float(total_expenses),
                "profit": float(total_sales - total_expenses),
                "sales_count": invoices.count(),
            }
        )


class ReportTrendView(APIView):
    """Sales received vs expenses recorded, bucketed over time — the trend chart's data."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        forbidden = _access_forbidden(request, team)
        if forbidden:
            return forbidden

        date_from, date_to = resolve_date_range(request)
        granularity = _choose_granularity(date_from, date_to)

        payments = Payment.objects.filter(invoice__team=team)
        expenses = Expense.objects.filter(team=team)
        if date_from:
            payments = payments.filter(recorded_at__date__gte=date_from)
            expenses = expenses.filter(expense_date__gte=date_from)
        if date_to:
            payments = payments.filter(recorded_at__date__lte=date_to)
            expenses = expenses.filter(expense_date__lte=date_to)

        buckets = defaultdict(lambda: {"sales": 0.0, "expenses": 0.0})
        for recorded_at, amount in payments.values_list("recorded_at", "amount"):
            buckets[_bucket_key(recorded_at.date(), granularity)]["sales"] += float(amount)
        for expense_date, amount in expenses.values_list("expense_date", "amount"):
            buckets[_bucket_key(expense_date, granularity)]["expenses"] += float(amount)

        points = [
            {"period": key, "sales": v["sales"], "expenses": v["expenses"], "profit": v["sales"] - v["expenses"]}
            for key, v in sorted(buckets.items())
        ]
        return Response({"granularity": granularity, "points": points})


class ReportExpenseBreakdownView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        forbidden = _access_forbidden(request, team)
        if forbidden:
            return forbidden

        date_from, date_to = resolve_date_range(request)
        expenses = Expense.objects.filter(team=team)
        if date_from:
            expenses = expenses.filter(expense_date__gte=date_from)
        if date_to:
            expenses = expenses.filter(expense_date__lte=date_to)

        rows = expenses.values("category").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
        labels = dict(Expense.Category.choices)

        return Response(
            [
                {
                    "category": row["category"],
                    "category_display": labels.get(row["category"], row["category"]),
                    "total": float(row["total"] or 0),
                    "count": row["count"],
                }
                for row in rows
            ]
        )


class ReportTopCustomersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        forbidden = _access_forbidden(request, team)
        if forbidden:
            return forbidden

        date_from, date_to = resolve_date_range(request)
        payments = Payment.objects.filter(invoice__team=team, invoice__customer__isnull=False)
        if date_from:
            payments = payments.filter(recorded_at__date__gte=date_from)
        if date_to:
            payments = payments.filter(recorded_at__date__lte=date_to)

        rows = (
            payments.values("invoice__customer_id", "invoice__customer__name")
            .annotate(total=Sum("amount"), sales_count=Count("invoice", distinct=True))
            .order_by("-total")[:10]
        )

        return Response(
            [
                {
                    "customer_id": str(row["invoice__customer_id"]),
                    "customer_name": row["invoice__customer__name"],
                    "total": float(row["total"] or 0),
                    "sales_count": row["sales_count"],
                }
                for row in rows
            ]
        )


class ReportExportView(APIView):
    """
    Plain CSV, deliberately not PDF: opens directly in Excel/Sheets for
    an accountant, needs no new rendering dependency, and covers the
    "take this to my accountant" case this exists for. A styled PDF
    later is a natural addition on top of this same data — not built
    now.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        forbidden = _access_forbidden(request, team)
        if forbidden:
            return forbidden

        date_from, date_to = resolve_date_range(request)
        invoices = Invoice.objects.filter(team=team)
        expenses = Expense.objects.filter(team=team)
        if date_from:
            invoices = invoices.filter(recorded_at__date__gte=date_from)
            expenses = expenses.filter(expense_date__gte=date_from)
        if date_to:
            invoices = invoices.filter(recorded_at__date__lte=date_to)
            expenses = expenses.filter(expense_date__lte=date_to)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="yousual-report.csv"'
        writer = csv.writer(response)
        writer.writerow(["Type", "Date", "Number", "Description", "Category/Customer", "Amount", "Status"])
        for inv in invoices.order_by("recorded_at"):
            writer.writerow(["Sale", inv.created_at_display, inv.invoice_number, inv.customer_name, "", inv.total, inv.status])
        for exp in expenses.order_by("expense_date"):
            writer.writerow(["Expense", exp.expense_date.strftime("%d %b %Y"), exp.expense_number, exp.title, exp.get_category_display(), exp.amount, ""])

        return response