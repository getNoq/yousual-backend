from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .emails import send_team_invite_email
from .models import Membership, TeamInvite
from .serializers import InviteMemberSerializer
from .services import get_active_team

# Future plan-gating hook — not enforced yet, per current instructions.
# Matches the "Up to 3 team members" line already promised on the
# Business Plan card in PlanSettings.tsx.
MAX_MEMBERS_BY_PLAN = {"free": 1, "business": 3}


class MembersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        if team is None:
            return Response({"message": "No team found."}, status=status.HTTP_404_NOT_FOUND)

        memberships = Membership.objects.filter(team=team).select_related("user").order_by("joined_at")
        pending_invites = TeamInvite.objects.filter(team=team, accepted_at__isnull=True)
        my_membership = memberships.get(user=request.user)

        return Response(
            {
                "team": {"id": str(team.id), "name": team.name, "plan": team.plan},
                "my_role": my_membership.role,
                "members": [
                    {
                        "id": str(m.id),
                        "name": f"{m.user.first_name} {m.user.last_name}".strip() or m.user.business_name,
                        "email": m.user.email,
                        "role": m.role,
                        "joined_at": m.joined_at,
                        "is_you": m.user_id == request.user.id,
                    }
                    for m in memberships
                ],
                "pending_invites": [
                    {"id": str(i.id), "email": i.email, "role": i.role, "created_at": i.created_at}
                    for i in pending_invites
                ],
            }
        )


class InviteMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        team = get_active_team(request.user)
        my_membership = Membership.objects.get(team=team, user=request.user)
        if my_membership.role not in (Membership.Role.OWNER, Membership.Role.ADMIN):
            return Response({"message": "Only owners and admins can invite team members."}, status=status.HTTP_403_FORBIDDEN)

        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]

        if Membership.objects.filter(team=team, user__email__iexact=email).exists():
            return Response({"message": "This person is already on your team."}, status=status.HTTP_400_BAD_REQUEST)

        invite = TeamInvite.objects.create(team=team, email=email, role=role, invited_by=request.user)
        send_team_invite_email(invite)
        return Response({"message": "Invite sent."}, status=status.HTTP_201_CREATED)


class RemoveMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, membership_id):
        team = get_active_team(request.user)
        my_membership = Membership.objects.get(team=team, user=request.user)
        try:
            target = Membership.objects.get(id=membership_id, team=team)
        except Membership.DoesNotExist:
            return Response({"message": "Member not found."}, status=status.HTTP_404_NOT_FOUND)

        if target.role == Membership.Role.OWNER:
            return Response({"message": "The team owner can't be removed."}, status=status.HTTP_400_BAD_REQUEST)
        if my_membership.role == Membership.Role.STAFF:
            return Response({"message": "Only owners and admins can remove members."}, status=status.HTTP_403_FORBIDDEN)
        if my_membership.role == Membership.Role.ADMIN and target.role == Membership.Role.ADMIN:
            return Response({"message": "Only the owner can remove another admin."}, status=status.HTTP_403_FORBIDDEN)

        target.delete()
        return Response({"message": "Member removed."})


class TeamInviteDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            invite = TeamInvite.objects.get(id=token, accepted_at__isnull=True)
        except TeamInvite.DoesNotExist:
            return Response({"message": "This invite is invalid or has already been used."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"team_name": invite.team.name, "email": invite.email, "role": invite.role})


class AcceptTeamInviteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        try:
            invite = TeamInvite.objects.get(id=token, accepted_at__isnull=True)
        except TeamInvite.DoesNotExist:
            return Response({"message": "This invite is invalid or has already been used."}, status=status.HTTP_404_NOT_FOUND)

        if request.user.email.lower() != invite.email.lower():
            return Response(
                {"message": f"This invite was sent to {invite.email}. Log in with that email to accept it."},
                status=status.HTTP_403_FORBIDDEN,
            )

        Membership.objects.get_or_create(team=invite.team, user=request.user, defaults={"role": invite.role})
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["accepted_at"])
        return Response({"message": f"You've joined {invite.team.name}."})


class MyTeamsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        memberships = Membership.objects.filter(user=request.user).select_related("team").order_by("joined_at")
        active_team = get_active_team(request.user)
        return Response(
            [
                {
                    "team_id": str(m.team.id),
                    "team_name": m.team.name,
                    "role": m.role,
                    "is_active": bool(active_team and m.team_id == active_team.id),
                }
                for m in memberships
            ]
        )


class SwitchTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        team_id = request.data.get("team_id")
        membership = Membership.objects.filter(team_id=team_id, user=request.user).first()
        if not membership:
            return Response({"message": "You're not a member of that team."}, status=status.HTTP_403_FORBIDDEN)
        request.user.active_team_id = team_id
        request.user.save(update_fields=["active_team_id"])
        return Response({"message": f"Switched to {membership.team.name}."})

class UpdateTeamBrandingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        team = get_active_team(request.user)
        membership = Membership.objects.filter(team=team, user=request.user).first()
        if not membership or membership.role != Membership.Role.OWNER:
            return Response({"message": "Only the team owner can change this."}, status=status.HTTP_403_FORBIDDEN)
        if team.plan != "business":
            return Response({"message": "This is a Business Plan feature."}, status=status.HTTP_403_FORBIDDEN)

        hide_branding = request.data.get("hide_branding")
        if hide_branding is None:
            return Response({"message": "hide_branding is required."}, status=status.HTTP_400_BAD_REQUEST)
        team.hide_branding = bool(hide_branding)
        team.save(update_fields=["hide_branding"])
        return Response({"hide_branding": team.hide_branding})