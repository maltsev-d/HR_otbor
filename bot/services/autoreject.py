from db.models import AutoRejectRule


FIELD_MAP = {
    "salary_amount": lambda c: c.salary_amount,
    "age":           lambda c: c.age,
    "languages":     lambda c: c.languages,   # строковое, пока не задействовано
    "work_type":     lambda c: c.work_type,   # строковое, пока не задействовано
}

CONDITION_MAP = {
    "gt":       lambda val, t: val is not None and _to_float(val) is not None and _to_float(val) > _to_float(t),
    "lt":       lambda val, t: val is not None and _to_float(val) is not None and _to_float(val) < _to_float(t),
    "eq":       lambda val, t: val is not None and str(val).strip().lower() == str(t).strip().lower(),
    "contains": lambda val, t: val is not None and str(t).strip().lower() in str(val).strip().lower(),
}


def _to_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def check_autoreject(session, candidate) -> bool:
    """True если кандидата нужно отклонить автоматически."""
    rules = session.query(AutoRejectRule).filter_by(is_active=True).all()
    for rule in rules:
        getter = FIELD_MAP.get(rule.field)
        cond   = CONDITION_MAP.get(rule.condition)
        if not getter or not cond:
            continue
        value = getter(candidate)
        try:
            if cond(value, rule.value):
                return True
        except Exception:
            continue
    return False