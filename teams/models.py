import uuid

from django.conf import settings
from django.db import models
from django.db.models import F


class Team(models.Model):
    class Plan(models.TextChoices):
        FREE = "free", "Free"
        BUSINESS = "business", "Business"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE)
    invoice_counter = models.PositiveIntegerField(default=0)
    expense_counter = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def _next_sequence_number(self, counter_field: str, prefix: str) -> str:
        Team.objects.filter(pk=self.pk).update(**{counter_field: F(counter_field) + 1})
        self.refresh_from_db(fields=[counter_field])
        return f"{prefix}-{getattr(self, counter_field):03d}"

    def next_invoice_number(self) -> str:
        return self._next_sequence_number("invoice_counter", "INV")

    def next_expense_number(self) -> str:
        return self._next_sequence_number("expense_counter", "EXP")


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["team", "user"], name="unique_membership_per_team_user")]

    def __str__(self):
        return f"{self.user.email} — {self.team.name} ({self.role})"


class TeamInvite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="invites")
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=Membership.Role.choices, default=Membership.Role.STAFF)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_invites")
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite to {self.email} for {self.team.name}"