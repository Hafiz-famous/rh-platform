# routes/overtime_admin.py
@admin_bp.post("/overtime/recompute") # pyright: ignore[reportUndefinedVariable]
def overtime_recompute():
    user_id = int(request.form["user_id"]) # pyright: ignore[reportUndefinedVariable]
    d1 = date.fromisoformat(request.form["from"]) # pyright: ignore[reportUndefinedVariable]
    d2 = date.fromisoformat(request.form["to"]) # pyright: ignore[reportUndefinedVariable]
    compute_overtime_for_range(user_id, d1, d2) # pyright: ignore[reportUndefinedVariable]
    return jsonify(ok=True) # pyright: ignore[reportUndefinedVariable]
