from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    """
    Reshapes DRF's default error response — {"email": ["already exists"]}
    — into {"message": "...", "errors": {"email": "already exists"}},
    matching what authApi.ts's ApiError expects on the frontend.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    if isinstance(data, dict):
        errors = {}
        message = None
        for field, value in data.items():
            first = value[0] if isinstance(value, list) and value else value
            if field in ("detail", "non_field_errors"):
                message = str(first)
            else:
                errors[field] = str(first)
        if message is None:
            message = next(iter(errors.values()), "Something went wrong. Please try again.")
        response.data = {"message": message, "errors": errors}

    return response