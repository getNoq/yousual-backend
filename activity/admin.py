from django.contrib import admin
from .models import EditLog


@admin.register(EditLog)
class EditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "content_type", "object_id", "changed_by", "created_at"]
    list_filter = ["action", "content_type"]