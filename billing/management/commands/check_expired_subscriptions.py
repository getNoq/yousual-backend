from django.core.management.base import BaseCommand

from billing.services import downgrade_expired_grace_periods


class Command(BaseCommand):
    help = "Downgrades any team whose grace period after a failed renewal has expired. Run daily via cron."

    def handle(self, *args, **options):
        count = downgrade_expired_grace_periods()
        self.stdout.write(self.style.SUCCESS(f"Downgraded {count} team(s) past their grace period."))