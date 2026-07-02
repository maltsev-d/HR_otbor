# services/autoreject.py
from db.models import AutoRejectRule

FIELD_MAP = {
    "salary_expectation": lambda c: c.salary_expectation,
    "age": lambda c: c.age,
}

CONDITION_MAP = {
    "gt": lambda val, threshold: val is not None and val > threshold,
    "lt": lambda val, threshold: val is not None and val < threshold,
}

def check_autoreject(session, candidate) -> bool:
    """True если кандидата надо отклонить автоматически."""
    rules = session.query(AutoRejectRule).filter_by(is_active=True).all()
    for rule in rules:
        getter = FIELD_MAP.get(rule.field)
        cond = CONDITION_MAP.get(rule.condition)
        if not getter or not cond:
            continue
        value = getter(candidate)
        try:
            threshold = float(rule.value)
        except ValueError:
            continue
        if cond(value, threshold):
            return True
    return False