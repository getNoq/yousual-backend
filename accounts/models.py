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
    first_name = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100, blank=True, default="")
    invoice_counter = models.PositiveIntegerField(default=0)
    expense_counter = models.PositiveIntegerField(default=0)
    active_team = models.ForeignKey("teams.Team", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    is_email_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone", "business_name"]

    def __str__(self):
        return self.email

    def _next_sequence_number(self, counter_field: str, prefix: str) -> str:
        """
        Atomically increments the given counter field (via F(), so two
        concurrent requests can't read the same starting value) and
        returns the next "{PREFIX}-XXX" number.
        """
        User.objects.filter(pk=self.pk).update(**{counter_field: F(counter_field) + 1})
        self.refresh_from_db(fields=[counter_field])
        return f"{prefix}-{getattr(self, counter_field):03d}"

    def next_invoice_number(self) -> str:
        return self._next_sequence_number("invoice_counter", "INV")

    def next_expense_number(self) -> str:
        return self._next_sequence_number("expense_counter", "EXP")