# utils.py

def validate_personal_number(pn: str) -> bool:
    if not pn:
        return False
    parts = pn.split('-')
    if len(parts) != 2:
        return False
    date_part, suffix = parts
    if len(date_part) != 8 or not date_part.isdigit():
        return False
    if len(suffix) != 4 or not suffix.isdigit():
        return False
    return True
