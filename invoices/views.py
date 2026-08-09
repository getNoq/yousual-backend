from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Invoice
from .serializers import ImportGuestInvoicesSerializer, InvoiceSerializer


class InvoiceListView(ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)


class MarkInvoicePaidView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        except Invoice.DoesNotExist:
            return Response({"message": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        invoice.status = Invoice.Status.PAID
        invoice.paid_date_display = request.data.get("paid_date", "")
        invoice.save(update_fields=["status", "paid_date_display"])
        return Response(InvoiceSerializer(invoice).data)


class ImportGuestInvoicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ImportGuestInvoicesSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        created = serializer.save()
        return Response({"imported": InvoiceSerializer(created, many=True).data}, status=status.HTTP_201_CREATED)