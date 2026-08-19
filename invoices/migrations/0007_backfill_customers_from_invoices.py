from django.db import migrations


def backfill_customers(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")
    Customer = apps.get_model("customers", "Customer")

    for invoice in Invoice.objects.filter(customer__isnull=True).order_by("recorded_at"):
        name = (invoice.customer_name or "").strip()
        if not name:
            continue
        phone = invoice.customer_phone or ""

        customer = None
        if phone:
            customer = Customer.objects.filter(user=invoice.user, phone=phone).first()
        if not customer:
            customer = Customer.objects.filter(user=invoice.user, name__iexact=name).first()
        if not customer:
            customer = Customer.objects.create(user=invoice.user, name=name, phone=phone)
        elif phone and not customer.phone:
            customer.phone = phone
            customer.save(update_fields=["phone"])

        invoice.customer = customer
        invoice.save(update_fields=["customer"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0006_invoice_customer'),
        ("customers", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(backfill_customers, noop_reverse),
    ]