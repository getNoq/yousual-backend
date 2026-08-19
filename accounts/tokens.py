from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Same time-limited, single-use signed-token mechanism as Django's
    built-in password reset generator, salted independently (a reset
    link can never double as a verification link or vice versa) and
    tied to is_email_verified + email — so it naturally stops working
    the instant verification succeeds, without a separate "used" flag.
    """

    key_salt = "accounts.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.is_email_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()