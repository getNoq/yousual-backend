from django.db import migrations
import secrets
import string

SLUG_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def backfill_slugs(apps, schema_editor):
    InvoiceShare = apps.get_model("invoices", "InvoiceShare")
    existing = set(InvoiceShare.objects.exclude(slug="").values_list("slug", flat=True))
    for share in InvoiceShare.objects.filter(slug=""):
        while True:
            slug = "".join(secrets.choice(SLUG_ALPHABET) for _ in range(8))
            if slug not in existing:
                existing.add(slug)
                break
        share.slug = slug
        share.save(update_fields=["slug"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("invoices", "0011_invoiceshare_slug")]
    operations = [migrations.RunPython(backfill_slugs, noop_reverse)]