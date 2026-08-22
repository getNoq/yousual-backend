from django.db import migrations


def backfill_teams(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Team = apps.get_model("teams", "Team")
    Membership = apps.get_model("teams", "Membership")
    Invoice = apps.get_model("invoices", "Invoice")
    Expense = apps.get_model("expenses", "Expense")
    Customer = apps.get_model("customers", "Customer")

    team_by_user_id = {}

    for user in User.objects.all():
        team = Team.objects.create(
            name=user.business_name or user.email,
            plan="free",
            invoice_counter=user.invoice_counter,
            expense_counter=user.expense_counter,
        )
        Membership.objects.create(team=team, user=user, role="owner")
        team_by_user_id[user.id] = team

    for invoice in Invoice.objects.filter(team__isnull=True):
        invoice.team = team_by_user_id.get(invoice.user_id)
        invoice.save(update_fields=["team"])

    for expense in Expense.objects.filter(team__isnull=True):
        expense.team = team_by_user_id.get(expense.user_id)
        expense.save(update_fields=["team"])

    for customer in Customer.objects.filter(team__isnull=True):
        customer.team = team_by_user_id.get(customer.user_id)
        customer.save(update_fields=["team"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("teams", "0001_initial"),
        ("accounts", "0005_user_is_email_verified"),
        ("invoices", "0008_invoice_team"),
        ("expenses", "0003_expense_team"),
        ("customers", "0002_customer_team"),
    ]
    operations = [
        migrations.RunPython(backfill_teams, noop_reverse),
    ]