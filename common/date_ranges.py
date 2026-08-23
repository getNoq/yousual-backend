from datetime import date, timedelta
from django.utils import timezone


def resolve_date_range(request):
    """
    One date-range filter convention for the whole app — Overview and
    Reports both call this instead of each keeping their own copy.
    "week" means the last 7 days (rolling), not the current calendar
    week; "month" means the current calendar month to date. Returns
    (date_from, date_to) as date objects, or (None, None) for "all".
    """
    range_param = request.query_params.get("range", "all")
    today = timezone.localdate()

    if range_param == "today":
        return today, today
    if range_param == "week":
        return today - timedelta(days=6), today
    if range_param == "month":
        return today.replace(day=1), today
    if range_param == "custom":
        raw_from = request.query_params.get("date_from")
        raw_to = request.query_params.get("date_to")
        try:
            df = date.fromisoformat(raw_from) if raw_from else None
            dt = date.fromisoformat(raw_to) if raw_to else None
            return df, dt
        except ValueError:
            return None, None
    return None, None