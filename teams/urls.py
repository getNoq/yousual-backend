from django.urls import path
from .views import AcceptTeamInviteView, InviteMemberView, MembersView, RemoveMemberView, TeamInviteDetailView

urlpatterns = [
    path("members/", MembersView.as_view(), name="team-members"),
    path("members/<uuid:membership_id>/", RemoveMemberView.as_view(), name="team-member-remove"),
    path("invites/", InviteMemberView.as_view(), name="team-invite"),
    path("invites/<uuid:token>/", TeamInviteDetailView.as_view(), name="team-invite-detail"),
    path("invites/<uuid:token>/accept/", AcceptTeamInviteView.as_view(), name="team-invite-accept"),
]