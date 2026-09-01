import uuid

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from teams.models import Membership, Team
from teams.services import get_active_team

from .gateways import GATEWAYS, get_gateway
from .models import BillingTransaction, PlanPrice, Subscription
from .services import activate_subscription, deactivate_subscription, mark_past_due


def _require_owner(request, team):
    membership = Membership.objects.filter(team=team, user=request.user).first()
    if not membership or membership.role != Membership.Role.OWNER:
        return Response({"message": "Only the team owner can manage billing."}, status=status.HTTP_403_FORBIDDEN)
    return None


class PlanPricesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        prices = PlanPrice.objects.all()
        return Response([{"interval": p.interval, "amount": float(p.amount)} for p in prices])


class SubscribeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        team = get_active_team(request.user)
        forbidden = _require_owner(request, team)
        if forbidden:
            return forbidden

        gateway_name = request.data.get("gateway", "paystack")
        interval = request.data.get("interval", "monthly")
        if gateway_name not in GATEWAYS:
            return Response({"message": "Unsupported payment method."}, status=status.HTTP_400_BAD_REQUEST)
        if interval not in ("monthly", "yearly"):
            return Response({"message": "Unsupported billing interval."}, status=status.HTTP_400_BAD_REQUEST)

        price = PlanPrice.objects.filter(interval=interval).first()
        if not price:
            return Response({"message": "Pricing isn't configured yet. Contact support."}, status=status.HTTP_400_BAD_REQUEST)
        plan_code = price.paystack_plan_code if gateway_name == "paystack" else price.flutterwave_plan_id
        if not plan_code:
            return Response({"message": "This plan isn't set up with the payment provider yet."}, status=status.HTTP_400_BAD_REQUEST)

        reference = f"yousual_{uuid.uuid4().hex[:20]}"
        gateway = get_gateway(gateway_name)
        try:
            result = gateway.initialize(
                email=request.user.email,
                amount=price.amount,
                plan_code=plan_code,
                callback_url=f"{settings.FRONTEND_URL}/dashboard/settings/billing/callback?gateway={gateway_name}",
                metadata={"team_id": str(team.id), "reference": reference, "interval": interval},
            )
        except Exception:
            return Response({"message": "Couldn't start checkout. Try again."}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"authorization_url": result["authorization_url"], "reference": result.get("reference", reference)})


class BillingStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        subscription = (
            Subscription.objects.filter(team=team, status__in=[Subscription.Status.ACTIVE, Subscription.Status.PAST_DUE])
            .order_by("-created_at")
            .first()
        )
        return Response(
            {
                "plan": team.plan,
                "is_comped": team.is_comped,
                "subscription": (
                    {
                        "gateway": subscription.gateway,
                        "interval": subscription.interval,
                        "status": subscription.status,
                        "current_period_end": subscription.current_period_end,
                        "grace_period_ends_at": subscription.grace_period_ends_at,
                        "amount": float(subscription.amount),
                    }
                    if subscription
                    else None
                ),
            }
        )


class CancelSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        team = get_active_team(request.user)
        forbidden = _require_owner(request, team)
        if forbidden:
            return forbidden

        subscription = Subscription.objects.filter(team=team, status__in=[Subscription.Status.ACTIVE, Subscription.Status.PAST_DUE]).first()
        if not subscription:
            return Response({"message": "No active subscription to cancel."}, status=status.HTTP_400_BAD_REQUEST)

        subscription.status = Subscription.Status.CANCELED
        subscription.grace_period_ends_at = None
        subscription.save(update_fields=["status", "grace_period_ends_at"])
        return Response({"message": "Subscription canceled. You'll keep Business Plan access until your current period ends."})


class VerifyCallbackView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        gateway_name = request.data.get("gateway", "paystack")
        reference = request.data.get("reference")
        if not reference or gateway_name not in GATEWAYS:
            return Response({"message": "Missing or invalid reference."}, status=status.HTTP_400_BAD_REQUEST)

        team = get_active_team(request.user)
        gateway = get_gateway(gateway_name)
        try:
            data = gateway.verify_transaction(reference)
        except Exception:
            return Response({"message": "Couldn't verify payment. It may still be processing."}, status=status.HTTP_502_BAD_GATEWAY)

        paid = data.get("status") in ("success", "successful")
        if not paid:
            return Response({"message": "Payment wasn't successful."}, status=status.HTTP_400_BAD_REQUEST)

        raw_amount = data.get("amount", 0)
        amount = (raw_amount / 100) if gateway_name == "paystack" else float(raw_amount)
        interval = (data.get("metadata") or {}).get("interval") or (data.get("meta") or {}).get("interval") or "monthly"
        activate_subscription(team, gateway_name, reference, amount, interval=interval)
        return Response({"message": "Business Plan activated.", "plan": "business"})


class BillingHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        forbidden = _require_owner(request, team)
        if forbidden:
            return forbidden

        transactions = BillingTransaction.objects.filter(team=team)[:50]
        return Response(
            [
                {"id": str(t.id), "gateway": t.gateway, "amount": float(t.amount), "status": t.status, "created_at": t.created_at}
                for t in transactions
            ]
        )


class PaystackWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser]

    def post(self, request):
        gateway = get_gateway("paystack")
        if not gateway.verify_webhook_signature(request):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        event = request.data
        event_type = event.get("event")
        data = event.get("data", {})

        if event_type == "charge.success":
            metadata = data.get("metadata", {}) or {}
            team_id = metadata.get("team_id")
            reference = data.get("reference")
            amount = (data.get("amount") or 0) / 100
            interval = metadata.get("interval", "monthly")
            if team_id and reference:
                team = Team.objects.filter(id=team_id).first()
                if team:
                    plan_object = data.get("plan_object") or {}
                    customer = data.get("customer") or {}
                    activate_subscription(
                        team, "paystack", reference, amount, interval=interval,
                        subscription_code=plan_object.get("plan_code", ""),
                        customer_code=customer.get("customer_code", ""),
                    )

        elif event_type == "invoice.payment_failed":
            subscription_code = data.get("subscription_code") or (data.get("subscription") or {}).get("subscription_code")
            if subscription_code:
                sub = Subscription.objects.filter(gateway="paystack", gateway_subscription_code=subscription_code).first()
                if sub:
                    mark_past_due(sub)

        elif event_type in ("subscription.disable", "subscription.not_renew"):
            subscription_code = data.get("subscription_code") or (data.get("subscription") or {}).get("subscription_code")
            if subscription_code:
                sub = Subscription.objects.filter(gateway="paystack", gateway_subscription_code=subscription_code).first()
                if sub:
                    deactivate_subscription(sub.team, "paystack")

        return Response(status=status.HTTP_200_OK)


class FlutterwaveWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser]

    def post(self, request):
        gateway = get_gateway("flutterwave")
        if not gateway.verify_webhook_signature(request):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.get("data", {})
        if data.get("status") in ("successful", "success"):
            meta = data.get("meta") or {}
            team_id = meta.get("team_id")
            reference = data.get("tx_ref") or data.get("flw_ref")
            amount = float(data.get("amount") or 0)
            interval = meta.get("interval", "monthly")
            if team_id and reference:
                team = Team.objects.filter(id=team_id).first()
                if team:
                    customer = data.get("customer") or {}
                    activate_subscription(team, "flutterwave", reference, amount, interval=interval, customer_code=str(customer.get("id", "")))

        return Response(status=status.HTTP_200_OK)