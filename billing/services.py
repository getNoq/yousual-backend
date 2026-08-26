from django.db import IntegrityError
from django.utils import timezone

from teams.models import Team

from .models import BillingTransaction, Subscription


def activate_subscription(team, gateway_name, reference, amount, subscription_code="", customer_code="", period_end=None):
    """
    The single place that actually flips a team onto Business Plan.
    Called from both the post-checkout verify endpoint (fast UX right
    after redirect) and the webhook handler (source of truth) — safe
    to call twice for the same reference, since gateway_reference is
    unique and a duplicate insert is simply swallowed as a no-op.
    """
    try:
        BillingTransaction.objects.create(
            team=team, gateway=gateway_name, gateway_reference=reference, amount=amount, status="success"
        )
    except IntegrityError:
        return False  # already processed this exact reference

    subscription, _ = Subscription.objects.get_or_create(
        team=team, gateway=gateway_name, defaults={"amount": amount, "status": Subscription.Status.ACTIVE}
    )
    subscription.status = Subscription.Status.ACTIVE
    subscription.amount = amount
    if subscription_code:
        subscription.gateway_subscription_code = subscription_code
    if customer_code:
        subscription.gateway_customer_code = customer_code
    subscription.current_period_end = period_end or (timezone.now() + timezone.timedelta(days=31))
    subscription.save()

    team.plan = Team.Plan.BUSINESS
    team.save(update_fields=["plan"])
    return True


def deactivate_subscription(team, gateway_name):
    team.plan = Team.Plan.FREE
    team.save(update_fields=["plan"])
    Subscription.objects.filter(team=team, gateway=gateway_name).update(status=Subscription.Status.CANCELED)