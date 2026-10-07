import string

from email_validator import EmailNotValidError, validate_email


def normalize_email(value):
    try:
        result = validate_email(
            value.strip(),
            check_deliverability=False, 
        )
    except EmailNotValidError:
        return None

    if len(result.normalized) > 255:
        return None

    return result.normalized.lower()

def is_valid_password(password):
    return (
        len(password) >= 8
        and any(character.isupper() for character in password)
        and any(character in string.digits for character in password)
        and any(character in string.punctuation for character in password)
    )