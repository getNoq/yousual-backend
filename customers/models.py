import uuid

from django.conf import settings
from django.db import models


class CustomerManager(models.Manager):
    def upsert_from_sale(self, user, name, phone):
        """
        Called every time a sale is recorded. Matches an existing
        customer by phone first (the more reliable identifier when
        present), falls back to an exact case-insensitive name match,
        and creates a new record only if neither matches. Backfills a
        phone number onto an existing name-matched customer if they
        didn't have one on file yet.
        """
        name = (name or "").strip()
        if not name:
            return None

        if phone:
            existing = self.filter(user=user, phone=phone).first()
            if existing:
                return existing

        existing = self.filter(user=user, name__iexact=name).first()
        if existing:
            if phone and not existing.phone:
                existing.phone = phone
                existing.save(update_fields=["phone"])
            return existing

        return self.create(user=user, name=name, phone=phone or "")


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=11, blank=True, default="")
    note = models.CharField(max_length=280, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CustomerManager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name