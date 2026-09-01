from rest_framework import status
from rest_framework.response import Response


def business_plan_required_response(feature_name: str):
    return Response(
        {"message": f"{feature_name} is a Business Plan feature. Upgrade to unlock it.", "code": "business_plan_required"},
        status=status.HTTP_403_FORBIDDEN,
    )