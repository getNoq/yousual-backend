from django.conf import settings
from django.core.mail import send_mail


def send_team_invite_email(invite):
    accept_link = f"{settings.FRONTEND_URL}/invite/{invite.id}"
    send_mail(
        subject=f"You've been invited to join {invite.team.name} on Yousual",
        message=(
            f"You've been invited to join {invite.team.name} on Yousual as {invite.get_role_display()}.\n\n"
            f"If you already have a Yousual account with this email, log in, then open this link to accept:\n{accept_link}\n\n"
            f"If you don't have an account yet, sign up with this exact email first, then open the link above."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invite.email],
        fail_silently=True,
    )