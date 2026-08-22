from rest_framework import serializers
from .models import Membership


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=[Membership.Role.ADMIN, Membership.Role.STAFF])

    def validate_email(self, value):
        return value.strip().lower()