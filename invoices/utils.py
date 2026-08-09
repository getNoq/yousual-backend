import re


def extract_invoice_seq(invoice_number: str) -> int:
    """
    Pulls the trailing number out of an invoice number like "INV-007"
    -> 7. Used to keep a user's server-side counter ahead of whatever
    sequence their guest-mode invoices already used.
    """
    match = re.search(r"(\d+)$", invoice_number or "")
    return int(match.group(1)) if match else 0