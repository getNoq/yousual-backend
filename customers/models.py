import uuid

from django.conf import settings
from django.db import models


class CustomerManager(models.Manager):
    def upsert_from_sale(self, team, user, name, phone):
        """
        Matches an existing customer for this team by phone first, then
        by exact case-insensitive name — creates a new one only if
        neither matches. `user` is still required because the legacy
        `user` column on Customer hasn't been dropped yet (see the
        expand-contract note); `team` is the real scoping field going
        forward.
        """
        name = (name or "").strip()
        if not name:
            return None

        if phone:
            existing = self.filter(team=team, phone=phone).first()
            if existing:
                return existing

        existing = self.filter(team=team, name__iexact=name).first()
        if existing:
            if phone and not existing.phone:
                existing.phone = phone
                existing.save(update_fields=["phone"])
            return existing

        return self.create(team=team, user=user, name=name, phone=phone or "")


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customers")
    team = models.ForeignKey("teams.Team", null=True, blank=True, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=11, blank=True, default="")
    note = models.CharField(max_length=280, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CustomerManager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name