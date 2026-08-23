from common.date_ranges import resolve_date_range as _resolve_date_range

from django.db.models import Q, Sum
from django.utils import timezone
from djangorestframework_camel_case.parser import CamelCaseFormParser, CamelCaseJSONParser, CamelCaseMultiPartParser
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from teams.models import Membership
from activity.services import diff_fields, log_change
from activity.models import EditLog

from invoices.models import Invoice, Payment
from invoices.pagination import InvoicePagination
from teams.services import get_active_team

from .models import Expense
from .serializers import CreateExpenseSerializer, ExpenseSerializer, ExpenseDetailSerializer, UpdateExpenseSerializer

PAGE_SIZE = InvoicePagination.page_size


class ExpenseListCreateView(ListAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination
    parser_classes = [CamelCaseMultiPartParser, CamelCaseFormParser, CamelCaseJSONParser]

    def get_queryset(self):
        team = get_active_team(self.request.user)
        return Expense.objects.filter(team=team)

    def get_serializer_context(self):
        return {"request": self.request}

    def post(self, request):
        if not request.user.is_email_verified:
            return Response(
                {"message": "Verify your email before recording new expenses.", "code": "email_not_verified"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CreateExpenseSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()
        return Response(
            ExpenseSerializer(expense, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ExpenseDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [CamelCaseMultiPartParser, CamelCaseFormParser, CamelCaseJSONParser]

    def get(self, request, expense_id):
        team = get_active_team(request.user)
        try:
            expense = Expense.objects.get(id=expense_id, team=team)
        except Expense.DoesNotExist:
            return Response({"message": "Expense not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ExpenseDetailSerializer(expense, context={"request": request}).data)

    def patch(self, request, expense_id):
        team = get_active_team(request.user)
        try:
            expense = Expense.objects.get(id=expense_id, team=team)
        except Expense.DoesNotExist:
            return Response({"message": "Expense not found."}, status=status.HTTP_404_NOT_FOUND)

        old_values = {
            "title": expense.title, "amount": str(expense.amount), "category": expense.category,
            "note": expense.note, "expense_date": str(expense.expense_date),
        }

        serializer = UpdateExpenseSerializer(expense, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        expense.last_edited_by = request.user
        expense.last_edited_at = timezone.now()
        expense.save(update_fields=["last_edited_by", "last_edited_at"])

        new_values = {
            "title": expense.title, "amount": str(expense.amount), "category": expense.category,
            "note": expense.note, "expense_date": str(expense.expense_date),
        }
        changes = diff_fields(old_values, new_values)
        if changes:
            log_change(expense, EditLog.Action.EDITED, request.user, changes)

        return Response(ExpenseDetailSerializer(expense, context={"request": request}).data)

    def delete(self, request, expense_id):
        team = get_active_team(request.user)
        membership = Membership.objects.filter(team=team, user=request.user).first()
        if not membership or membership.role != Membership.Role.OWNER:
            return Response({"message": "Only the team owner can delete expenses."}, status=status.HTTP_403_FORBIDDEN)

        try:
            expense = Expense.objects.get(id=expense_id, team=team)
        except Expense.DoesNotExist:
            return Response({"message": "Expense not found."}, status=status.HTTP_404_NOT_FOUND)

        expense.is_deleted = True
        expense.save(update_fields=["is_deleted"])
        log_change(expense, EditLog.Action.DELETED, request.user)
        return Response({"message": "Expense deleted."})


class OverviewSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        date_from, date_to = _resolve_date_range(request)

        payments = Payment.objects.filter(invoice__team=team)
        expenses = Expense.objects.filter(team=team)
        if date_from:
            payments = payments.filter(recorded_at__date__gte=date_from)
            expenses = expenses.filter(expense_date__gte=date_from)
        if date_to:
            payments = payments.filter(recorded_at__date__lte=date_to)
            expenses = expenses.filter(expense_date__lte=date_to)

        total_sales = payments.aggregate(s=Sum("amount"))["s"] or 0
        total_expenses = expenses.aggregate(s=Sum("amount"))["s"] or 0
        profit = total_sales - total_expenses

        open_invoices = Invoice.objects.filter(team=team).exclude(status=Invoice.Status.PAID)
        total_open = open_invoices.aggregate(s=Sum("total"))["s"] or 0
        total_paid_on_open = Payment.objects.filter(invoice__in=open_invoices).aggregate(s=Sum("amount"))["s"] or 0
        total_outstanding = total_open - total_paid_on_open

        return Response(
            {
                "total_sales": float(total_sales),
                "total_expenses": float(total_expenses),
                "profit": float(profit),
                "total_outstanding": float(total_outstanding),
            }
        )


class OverviewFeedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        type_param = request.query_params.get("type", "all")
        search = request.query_params.get("search", "").strip()
        sort = request.query_params.get("sort", "newest")
        date_from, date_to = _resolve_date_range(request)
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1

        items = []

        if type_param in ("all", "sale"):
            invoices = Invoice.objects.filter(team=team)
            if date_from:
                invoices = invoices.filter(recorded_at__date__gte=date_from)
            if date_to:
                invoices = invoices.filter(recorded_at__date__lte=date_to)
            if search:
                invoices = invoices.filter(customer_name__icontains=search)
            for inv in invoices:
                items.append(
                    {
                        "id": str(inv.id),
                        "type": "sale",
                        "number": inv.invoice_number,
                        "date": inv.recorded_at.date().isoformat(),
                        "date_display": inv.created_at_display,
                        "title": inv.customer_name,
                        "meta_label": "Receipt" if inv.status == Invoice.Status.PAID else "Invoice",
                        "amount": float(inv.total),
                        "status": inv.status,
                        "invoice_id": str(inv.id),
                        "expense_id": None,
                        "receipt_url": None,
                    }
                )

        if type_param in ("all", "expense"):
            expenses = Expense.objects.filter(team=team)
            if date_from:
                expenses = expenses.filter(expense_date__gte=date_from)
            if date_to:
                expenses = expenses.filter(expense_date__lte=date_to)
            if search:
                expenses = expenses.filter(Q(title__icontains=search) | Q(category__icontains=search) | Q(note__icontains=search))
            for exp in expenses:
                items.append(
                    {
                        "id": str(exp.id),
                        "type": "expense",
                        "number": exp.expense_number,
                        "date": exp.expense_date.isoformat(),
                        "date_display": exp.expense_date.strftime("%d %b %Y"),
                        "title": exp.title,
                        "meta_label": exp.get_category_display(),
                        "amount": float(exp.amount),
                        "status": None,
                        "invoice_id": None,
                        "expense_id": str(exp.id),
                        "receipt_url": request.build_absolute_uri(exp.receipt.url) if exp.receipt else None,
                    }
                )

        reverse = sort in ("newest", "amount_desc")
        if sort in ("newest", "oldest"):
            items.sort(key=lambda i: i["date"], reverse=reverse)
        else:
            items.sort(key=lambda i: i["amount"], reverse=reverse)

        count = len(items)
        start = (page - 1) * PAGE_SIZE
        page_items = items[start : start + PAGE_SIZE]

        return Response({"count": count, "results": page_items})