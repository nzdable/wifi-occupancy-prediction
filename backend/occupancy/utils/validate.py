import re

SAFE = re.compile(r"^[a-z0-9_.-]+$")  # allow a–z, 0–9, underscore, dot, dash (lowercase)

def clean_choice(val: str | None, default: str, choices: set[str] | None = None) -> str:
    """
    Normalize query param values and guard against unsafe characters.
    - trims, strips quotes, lowercases
    - enforces an allowed character set
    - optionally enforces membership in a choices set
    """
    v = (val or default).strip().strip('"').strip("'").lower()
    if choices and v not in choices:
        raise ValueError(f"Invalid value '{v}'. Allowed: {sorted(choices)}")
    if not SAFE.match(v):
        raise ValueError(f"Unsafe characters in '{v}'. Only [a-z0-9_.-] allowed.")
    return v
