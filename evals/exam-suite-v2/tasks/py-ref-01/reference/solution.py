NO_NAME = "no_name"
NO_AGE = "no_age"
NO_EMAIL = "no_email"
AGE_MINOR = "age_minor"
AGE_IMPOSSIBLE = "age_impossible"
EMAIL_BAD = "email_bad"


def _check_name(data, errors):
    if "name" not in data:
        errors.append(NO_NAME)


def _check_age(data, errors):
    if "age" not in data:
        errors.append(NO_AGE)
        return
    age = data["age"]
    if age < 18:
        errors.append(AGE_MINOR)
    elif age > 150:
        errors.append(AGE_IMPOSSIBLE)


def _check_email(data, errors):
    if "email" not in data:
        errors.append(NO_EMAIL)
        return
    email = data["email"]
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        errors.append(EMAIL_BAD)


def validate_form(data):
    errors = []
    for check in (_check_name, _check_age, _check_email):
        check(data, errors)
    return errors
