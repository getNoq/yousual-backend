from django.db.models import Sum
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from common.plan_gating import business_plan_required_response
from invoices.models import Invoice, Payment
from invoices.pagination import InvoicePagination
from invoices.serializers import InvoiceSerializer
from teams.services import get_active_team

from .models import Customer
from .serializers import CustomerSerializer, UpdateCustomerSerializer


class CustomerListView(ListAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination

    def get_queryset(self):
        team = get_active_team(self.request.user)
        qs = Customer.objects.filter(team=team)
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def list(self, request, *args, **kwargs):
        team = get_active_team(request.user)
        if not team or team.plan != "business":
            return business_plan_required_response("Customer history")
        return super().list(request, *args, **kwargs)


class CustomerDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, customer_id):
        team = get_active_team(request.user)
        if not team or team.plan != "business":
            return business_plan_required_response("Customer history")
        try:
            customer = Customer.objects.get(id=customer_id, team=team)
        except Customer.DoesNotExist:
            return Response({"message": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        invoices = Invoice.objects.filter(customer=customer)
        total_spent = invoices.aggregate(s=Sum("total"))["s"] or 0
        total_paid = Payment.objects.filter(invoice__customer=customer).aggregate(s=Sum("amount"))["s"] or 0

        return Response(
            {
                "customer": CustomerSerializer(customer).data,
                "total_sales_count": invoices.count(),
                "total_spent": float(total_spent),
                "total_paid": float(total_paid),
                "invoices": InvoiceSerializer(invoices, many=True).data,
            }
        )

    def patch(self, request, customer_id):
        team = get_active_team(request.user)
        if not team or team.plan != "business":
            return business_plan_required_response("Customer history")
        try:
            customer = Customer.objects.get(id=customer_id, team=team)
        except Customer.DoesNotExist:
            return Response({"message": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateCustomerSerializer(customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CustomerSerializer(customer).data)