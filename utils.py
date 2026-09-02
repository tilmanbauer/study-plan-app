# utils.py
import re

def _luhn_checksum(digits: str) -> bool:
    if len(digits) != 10 or not digits.isdigit():
        return False
    total = 0
    for i, d in enumerate(digits):
        value = int(d) * (2 if i % 2 == 0 else 1)
        total += value // 10 + value % 10
    return total % 10 == 0


def validate_personal_number(pn: str) -> bool:
    if not pn:
        return False

    # Temporary university-assigned number: YYYYMMDD-TNNN
    if re.fullmatch(r"\d{8}-T\d{3}", pn):
        return True

    # Standard Swedish personal number: YYYYMMDD-NNNN
    match = re.fullmatch(r"(\d{8})-(\d{4})", pn)
    if not match:
        return False

    date_part, suffix = match.groups()

    # Validate date
    try:
        from datetime import datetime
        datetime.strptime(date_part, "%Y%m%d")
    except ValueError:
        return False

    # Validate Luhn checksum on the last 9 digits of the full 12-digit number
    full = date_part + suffix
    return _luhn_checksum(full[2:])
