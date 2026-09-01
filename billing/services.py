from django.db import IntegrityError
from django.utils import timezone

from teams.models import Team

from .models import BillingTransaction, Subscription

GRACE_PERIOD_DAYS = 3


def activate_subscription(team, gateway_name, reference, amount, interval="monthly", subscription_code="", customer_code="", period_end=None):
    try:
        BillingTransaction.objects.create(
            team=team, gateway=gateway_name, gateway_reference=reference, amount=amount, status="success"
        )
    except IntegrityError:
        return False  # already processed this exact reference

    subscription, _ = Subscription.objects.get_or_create(
        team=team, gateway=gateway_name, defaults={"amount": amount, "status": Subscription.Status.ACTIVE, "interval": interval}
    )
    subscription.status = Subscription.Status.ACTIVE
    subscription.amount = amount
    subscription.interval = interval
    subscription.grace_period_ends_at = None  # a successful charge clears any prior grace period
    if subscription_code:
        subscription.gateway_subscription_code = subscription_code
    if customer_code:
        subscription.gateway_customer_code = customer_code
    if period_end is None:
        days = 366 if interval == "yearly" else 31
        period_end = timezone.now() + timezone.timedelta(days=days)
    subscription.current_period_end = period_end
    subscription.save()

    team.plan = Team.Plan.BUSINESS
    team.save(update_fields=["plan"])
    return True


def deactivate_subscription(team, gateway_name):
    team.plan = Team.Plan.FREE
    team.save(update_fields=["plan"])
    Subscription.objects.filter(team=team, gateway=gateway_name).update(status=Subscription.Status.CANCELED, grace_period_ends_at=None)


def mark_past_due(subscription):
    """
    A single failed renewal doesn't cut access immediately — the
    gateway retries automatically over the following days. Business
    Plan access continues through the grace period; downgrade_expired
    _grace_periods() is what actually removes it, once genuinely
    unresolved.
    """
    subscription.status = Subscription.Status.PAST_DUE
    subscription.grace_period_ends_at = timezone.now() + timezone.timedelta(days=GRACE_PERIOD_DAYS)
    subscription.save(update_fields=["status", "grace_period_ends_at"])


def downgrade_expired_grace_periods():
    """Called by the check_expired_subscriptions management command — run this daily via cron."""
    expired = Subscription.objects.filter(status=Subscription.Status.PAST_DUE, grace_period_ends_at__lte=timezone.now())
    count = 0
    for sub in expired:
        deactivate_subscription(sub.team, sub.gateway)
        count += 1
    return count