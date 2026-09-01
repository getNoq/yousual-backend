from decimal import Decimal
from django.db import migrations


def seed_prices(apps, schema_editor):
    PlanPrice = apps.get_model("billing", "PlanPrice")
    PlanPrice.objects.get_or_create(interval="monthly", defaults={"amount": Decimal("5000")})
    PlanPrice.objects.get_or_create(interval="yearly", defaults={"amount": Decimal("50000")})


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("billing", "0002_planprice_subscription_grace_period_ends_at_and_more")]
    operations = [migrations.RunPython(seed_prices, noop_reverse)]