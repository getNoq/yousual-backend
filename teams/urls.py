from django.urls import path
from .views import AcceptTeamInviteView, InviteMemberView, MembersView, MyTeamsView, RemoveMemberView, SwitchTeamView, TeamInviteDetailView, UpdateTeamBrandingView

urlpatterns = [
    path("members/", MembersView.as_view(), name="team-members"),
    path("members/<uuid:membership_id>/", RemoveMemberView.as_view(), name="team-member-remove"),
    path("invites/", InviteMemberView.as_view(), name="team-invite"),
    path("invites/<uuid:token>/", TeamInviteDetailView.as_view(), name="team-invite-detail"),
    path("invites/<uuid:token>/accept/", AcceptTeamInviteView.as_view(), name="team-invite-accept"),
    path("my-teams/", MyTeamsView.as_view(), name="team-my-teams"),
    path("switch/", SwitchTeamView.as_view(), name="team-switch"),
    path("branding/", UpdateTeamBrandingView.as_view(), name="team-branding"),
]