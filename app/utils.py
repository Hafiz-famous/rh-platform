from math import floor

def fmt_hours(value: float | int | None) -> str:
    """Affiche 0.35 h -> 21 min ; 1.75 -> 1 h 45"""
    if value is None:
        return "—"
    minutes = round(float(value) * 60)
    if minutes < 60:
        return f"{minutes} min"
    h, m = divmod(minutes, 60)
    return f"{h} h {m:02d}"
