import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class EditLog(models.Model):
    class Action(models.TextChoices):
        EDITED = "edited", "Edited"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    record = GenericForeignKey("content_type", "object_id")

    action = models.CharField(max_length=10, choices=Action.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="edit_logs")
    # {"field_name": {"old": ..., "new": ...}} — a precise diff rather
    # than two full before/after documents, so the owner can see
    # exactly what changed without comparing two whole records by eye.
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_action_display()} {self.content_type.model} {self.object_id} by {self.changed_by}"