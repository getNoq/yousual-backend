from django.utils import timezone
from .models import Membership, TeamInvite


def get_active_team(user):
    """
    A user's "current" team. Prefers a non-owner membership over their
    own auto-created solo team, on the assumption that if you were
    invited somewhere, that's why you're here right now. There's no
    team-switcher UI yet — this is a deliberate placeholder heuristic
    until multiple real memberships are common enough to need one.
    """
    memberships = list(user.memberships.select_related("team").all())
    if not memberships:
        return None
    non_owner = [m for m in memberships if m.role != Membership.Role.OWNER]
    chosen = non_owner[0] if non_owner else memberships[0]
    return chosen.team


def accept_invite_if_valid(user, token):
    """
    Best-effort invite acceptance, called right after signup/login when
    the person arrived via an invite link — so they don't have to click
    back into the email a second time. Silently does nothing (returns
    None) if the token is missing, invalid, already used, or doesn't
    match the logged-in user's email — those are all "not applicable"
    here, not errors, since this always rides along with the real
    action (signing up / logging in), never blocks it.
    """
    if not token:
        return None
    try:
        invite = TeamInvite.objects.get(id=token, accepted_at__isnull=True)
    except (TeamInvite.DoesNotExist, ValueError, ValidationError := Exception):
        return None
    if user.email.lower() != invite.email.lower():
        return None

    Membership.objects.get_or_create(team=invite.team, user=user, defaults={"role": invite.role})
    invite.accepted_at = timezone.now()
    invite.save(update_fields=["accepted_at"])
    return invite.team.name