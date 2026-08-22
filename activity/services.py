from django.contrib.contenttypes.models import ContentType
from .models import EditLog


def log_change(instance, action, changed_by, changes=None):
    EditLog.objects.create(
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.pk,
        action=action,
        changed_by=changed_by,
        changes=changes or {},
    )


def get_edit_history(instance):
    content_type = ContentType.objects.get_for_model(instance)
    return EditLog.objects.filter(content_type=content_type, object_id=instance.pk)


def diff_fields(old_values: dict, new_values: dict) -> dict:
    changes = {}
    for field, new_value in new_values.items():
        if old_values.get(field) != new_value:
            changes[field] = {"old": old_values.get(field), "new": new_value}
    return changes