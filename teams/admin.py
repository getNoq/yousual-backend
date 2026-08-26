from django.contrib import admin
from .models import Membership, Team, TeamInvite


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "plan", "is_comped", "created_at"]
    list_filter = ["plan", "is_comped"]
    actions = ["grant_business_plan", "revoke_business_plan"]

    @admin.action(description="Grant Business Plan access (comp)")
    def grant_business_plan(self, request, queryset):
        updated = queryset.update(plan=Team.Plan.BUSINESS, is_comped=True)
        self.message_user(request, f"{updated} team(s) granted Business Plan access.")

    @admin.action(description="Revoke comped Business Plan access")
    def revoke_business_plan(self, request, queryset):
        updated = queryset.filter(is_comped=True).update(plan=Team.Plan.FREE, is_comped=False)
        self.message_user(request, f"{updated} comped team(s) reverted to Free.")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["team", "user", "role", "joined_at"]


@admin.register(TeamInvite)
class TeamInviteAdmin(admin.ModelAdmin):
    list_display = ["team", "email", "role", "accepted_at", "created_at"]