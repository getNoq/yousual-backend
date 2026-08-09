import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models import F

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=11)
    business_name = models.CharField(max_length=255)
    # Server-side sequence for invoices created from the dashboard.
    # Bumped past whatever guest-mode invoices were imported for this
    # user too, so the two numbering sources never collide — see
    # invoices/utils.py:extract_invoice_seq.
    invoice_counter = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone", "business_name"]

    def __str__(self):
        return self.email

    def next_invoice_number(self) -> str:
        """
        Atomically increments this user's invoice counter (via an F()
        expression, so two concurrent requests can't both read the
        same starting value) and returns the next "INV-XXX" number.
        """
        User.objects.filter(pk=self.pk).update(invoice_counter=F("invoice_counter") + 1)
        self.refresh_from_db(fields=["invoice_counter"])
        return f"INV-{self.invoice_counter:03d}"