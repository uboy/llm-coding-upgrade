def validate_form(data):
    errors = []
    if "name" not in data:
        errors.append("no_name")
    if "age" not in data:
        errors.append("no_age")
    else:
        a = data["age"]
        if a < 18:
            errors.append("age_minor")
        elif a > 150:
            errors.append("age_impossible")
    if "email" not in data:
        errors.append("no_email")
    else:
        e = data["email"]
        if "@" not in e or e.endswith("@") or e.startswith("@"):
            errors.append("email_bad")
    return errors
