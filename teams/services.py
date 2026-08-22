from .models import Membership


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