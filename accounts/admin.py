from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "business_name", "phone", "is_staff"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Business info", {"fields": ("business_name", "phone")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "business_name", "phone", "password1", "password2"),
            },
        ),
    )
    search_fields = ["email", "business_name"]
    readonly_fields = ["date_joined"]


admin.site.register(User, UserAdmin)