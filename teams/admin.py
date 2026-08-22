from django.contrib import admin
from .models import Membership, Team, TeamInvite


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "plan", "created_at"]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["team", "user", "role", "joined_at"]


@admin.register(TeamInvite)
class TeamInviteAdmin(admin.ModelAdmin):
    list_display = ["team", "email", "role", "accepted_at", "created_at"]