from django.db import migrations


def backfill_payments(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")
    Payment = apps.get_model("invoices", "Payment")

    for invoice in Invoice.objects.filter(status="paid"):
        if not Payment.objects.filter(invoice=invoice).exists():
            Payment.objects.create(
                invoice=invoice,
                amount=invoice.total,
                paid_date_display=invoice.paid_date_display or invoice.created_at_display,
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0004_invoiceshare_amount_paid_alter_invoice_status_and_more'),
    ]
    operations = [
        migrations.RunPython(backfill_payments, noop_reverse),
    ]
