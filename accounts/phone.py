import re
from rest_framework import serializers

# Same five valid Nigerian mobile prefixes as the frontend's lib/phone.ts —
# keep these in sync if either side changes.
NG_PHONE_PATTERN = re.compile(r"^(70|80|81|90|91)\d{8}$")


def normalize_ng_phone(raw: str) -> str:
    """
    Mirrors the frontend's normalizeNGPhone: accepts either 11 digits
    starting with 0, or 10 digits with no leading 0. Returns local
    "0XXXXXXXXXX" format. Raises ValidationError if invalid.
    """
    digits = re.sub(r"\D", "", raw or "")

    if len(digits) == 11 and digits.startswith("0"):
        rest = digits[1:]
    elif len(digits) == 10 and not digits.startswith("0"):
        rest = digits
    else:
        rest = None

    if not rest or not NG_PHONE_PATTERN.match(rest):
        raise serializers.ValidationError("Enter a valid Nigerian number, e.g. 08031234567.")

    return "0" + rest