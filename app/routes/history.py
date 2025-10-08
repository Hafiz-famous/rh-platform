from datetime import datetime, time, timedelta
from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.extensions import db
from app.models import User, Role  # imports sûrs

# -------------------------
# Résolution tolérante des modèles
# -------------------------
def _resolve_model():
    out = {"Attendance": None, "Leave": None, "Overtime": None}

    def _try(paths):
        for mod_path, cls_name in paths:
            try:
                mod = __import__(mod_path, fromlist=[cls_name])
                return getattr(mod, cls_name)
            except Exception:
                continue
        return None

    out["Attendance"] = _try([
        ("app.models", "Attendance"),
        ("app.models.attendance", "Attendance"),
        ("app.models.attendance", "Timesheet"),
        ("app.models.timesheet", "Attendance"),
        ("app.models.timesheet", "Timesheet"),
    ])

    out["Leave"] = _try([
        ("app.models", "LeaveRequest"),
        ("app.models.leave", "LeaveRequest"),
        ("app.models.leave", "Leave"),
        ("app.models.leave", "LeaveApplication"),
        ("app.models.leave", "LeaveRecord"),
    ])

    out["Overtime"] = _try([
        ("app.models", "Overtime"),
        ("app.models.overtime", "Overtime"),
        ("app.models.overtime", "OvertimeRequest"),
        ("app.models.extra_hours", "Overtime"),
        ("app.models.extra_hours", "ExtraHours"),
    ])
    return out

MODELS = _resolve_model()
Attendance = MODELS["Attendance"]
Leave      = MODELS["Leave"]
Overtime   = MODELS["Overtime"]

bp = Blueprint("history", __name__, url_prefix="/history")

@bp.app_context_processor
def _ctx_flags():
    return {
        "ATTENDANCE_ENABLED": Attendance is not None,
        "LEAVE_ENABLED": Leave is not None,
        "OVERTIME_ENABLED": Overtime is not None,
    }

# -------------------------
# Helpers
# -------------------------
def _parse_dates():
    fmt = "%Y-%m-%d"
    sd = request.args.get("start_date")
    ed = request.args.get("end_date")
    today = datetime.utcnow().date()
    start = datetime.combine(datetime.strptime(sd, fmt).date() if sd else (today - timedelta(days=30)), time.min)
    end   = datetime.combine(datetime.strptime(ed, fmt).date() if ed else today, time.max)
    return start, end

def _is_column(attr):
    return isinstance(attr, (InstrumentedAttribute, ColumnElement))

def _as_column(model, name):
    attr = getattr(model, name, None)
    return attr if _is_column(attr) else None

def _q_user_filter(q: str):
    if not q:
        return True
    like = f"%{q.strip()}%"
    ors = []
    for name in ("full_name", "name", "first_name", "last_name", "email", "username"):
        col = _as_column(User, name)
        if col is not None:
            ors.append(col.ilike(like))
    return or_(*ors) if ors else True

def _display_name(u: User) -> str:
    fn_prop = getattr(u, "full_name", None)
    if isinstance(fn_prop, str) and fn_prop:
        return fn_prop
    first = getattr(u, "first_name", "") or ""
    last  = getattr(u, "last_name", "") or ""
    nm = (first + " " + last).strip()
    if nm:
        return nm
    return getattr(u, "name", "") or getattr(u, "email", "") or str(getattr(u, "id", ""))

def _has_attr(model, name):
    try:
        getattr(model, name)
        return True
    except Exception:
        return False

def _with_user_join(qry, model, already_joined=False):
    if already_joined:
        return qry, True
    try:
        return qry.join(User), True
    except Exception:
        return qry, False

def _apply_user_filter(qry, model, user_id):
    """Filtre by user_id en priorité via FK, sinon JOIN(User)."""
    if not user_id:
        return qry, False
    if _has_attr(model, "user_id"):
        return qry.filter(getattr(model, "user_id") == user_id), False
    qry, joined = _with_user_join(qry, model)
    return qry.filter(User.id == user_id), True

def _user_label(obj):
    u = getattr(obj, "user", None)
    if u:
        return getattr(u, "full_name", None) or \
               (" ".join(filter(None, [getattr(u, "first_name", ""), getattr(u, "last_name", "")])).strip()) or \
               getattr(u, "name", "") or getattr(u, "email", "") or f"#{getattr(u,'id','')}"
    uid = getattr(obj, "user_id", None)
    return f"#{uid}" if uid is not None else "—"

# -------------------------
# Routes
# -------------------------
@bp.get("/")
@login_required
def index():
    if not (current_user.is_authenticated and current_user.has_role(Role.ADMIN, Role.MANAGER)):
        abort(403)

    users = User.query.all()
    users.sort(key=lambda u: _display_name(u).lower())

    requested = request.args.get("tab", "leaves")
    available = []
    if Leave is not None:      available.append("leaves")
    if Attendance is not None: available.append("attendance")
    if Overtime is not None:   available.append("overtime")

    if not available:
        return render_template("history/index.html", users=users, active_tab=None)

    active = requested if requested in available else available[0]
    return render_template("history/index.html", users=users, active_tab=active)

@bp.get("/search")
@login_required
def search():
    if not (current_user.is_authenticated and current_user.has_role(Role.ADMIN, Role.MANAGER)):
        abort(403)

    start, end = _parse_dates()
    user_id = request.args.get("user_id", type=int)
    tab = request.args.get("type") or request.args.get("tab") or "leaves"
    q = request.args.get("q") or request.args.get("search")

    # ----- OVERTIME -----
    if tab == "overtime":
        if Overtime is None:
            return render_template("history/partials/overtime_table.html", items=[])

        qry = db.session.query(Overtime)

        # (facultatif) charger user si relation définie
        if _has_attr(Overtime, "user"):
            qry = qry.options(joinedload(getattr(Overtime, "user")))

        # filtre user sûr (FK user_id)
        if user_id:
            qry = qry.filter(Overtime.user_id == user_id)

        # période : **work_date** (DATE dans ton modèle)
        qry = qry.filter(Overtime.work_date >= start.date(),
                         Overtime.work_date <= end.date())
        order_col = Overtime.work_date

        # filtre origine (colonne **source**)
        origin = request.args.get("origin") or request.args.get("ot_origin")
        if origin:
            qry = qry.filter(Overtime.source == origin)  # 'auto' ou 'manual'

        # filtre statut si fourni
        status = request.args.get("status")
        if status:
            qry = qry.filter(Overtime.status == status)

        # recherche texte (note + éventuellement utilisateur si joint)
        if q:
            like = f"%{q.strip()}%"
            try:
                qry = qry.join(User).filter(or_(_q_user_filter(q), Overtime.note.ilike(like)))
            except Exception:
                qry = qry.filter(Overtime.note.ilike(like))

        rows = qry.order_by(order_col.desc(), Overtime.id.desc()).limit(1000).all()

        data = [{
            "id": r.id,
            "user": _user_label(r),
            "type": "Automatique" if (getattr(r, "source", "") == "auto") else "Manuelle",
            "start": r.work_date,
            "end":   r.work_date,
            "hours": float(getattr(r, "hours", 0) or 0),
            "status": getattr(r, "status", "") or "",
            "note": getattr(r, "note", "") or ""
        } for r in rows]

        return render_template("history/partials/overtime_table.html", items=data)

    # ----- ATTENDANCE -----
    if tab == "attendance":
        if Attendance is None:
            return render_template("history/partials/attendance_table.html", items=[])

        qry = db.session.query(Attendance)
        if _has_attr(Attendance, "user"):
            qry = qry.options(joinedload(getattr(Attendance, "user")))

        qry, joined_user = _apply_user_filter(qry, Attendance, user_id)

        if _has_attr(Attendance, "work_date"):
            qry = qry.filter(Attendance.work_date >= start.date(), Attendance.work_date <= end.date())
            order_col = getattr(Attendance, "work_date")
        elif _has_attr(Attendance, "check_in"):
            qry = qry.filter(getattr(Attendance, "check_in") >= start,
                             getattr(Attendance, "check_in") <= end)
            order_col = getattr(Attendance, "check_in")
        else:
            order_col = getattr(Attendance, "id")

        if q:
            if not joined_user:
                qry, _ = _with_user_join(qry, Attendance, already_joined=False)
            qry = qry.filter(_q_user_filter(q))

        rows = qry.order_by(order_col.desc()).limit(1000).all()

        def _hours_att(a):
            val = getattr(a, "worked_hours", None)
            if val is not None:
                try:
                    return float(val)
                except Exception:
                    pass
            ci = getattr(a, "check_in", None); co = getattr(a, "check_out", None)
            return round((co - ci).total_seconds()/3600, 2) if ci and co else 0.0

        data = [{
            "id": a.id,
            "user": _user_label(a),
            "date": getattr(a, "work_date", None) or (a.check_in.date() if getattr(a, "check_in", None) else None),
            "in": getattr(a, "check_in", None),
            "out": getattr(a, "check_out", None),
            "hours": _hours_att(a),
            "note": getattr(a, "note", "")
        } for a in rows]

        return render_template("history/partials/attendance_table.html", items=data)

    # ----- LEAVES (par défaut) -----
    if Leave is None:
        return render_template("history/partials/leaves_table.html", items=[])

    qry = db.session.query(Leave)
    if _has_attr(Leave, "user"):
        qry = qry.options(joinedload(getattr(Leave, "user")))

    qry, joined_user = _apply_user_filter(qry, Leave, user_id)

    start_col = getattr(Leave, "start_date", None) or getattr(Leave, "from_date", None)
    end_col   = getattr(Leave, "end_date", None)   or getattr(Leave, "to_date", None)
    if start_col is not None and end_col is not None:
        qry = qry.filter(end_col >= start.date(), start_col <= end.date())
        order_col = start_col
    else:
        order_col = getattr(Leave, "id")

    if _has_attr(Leave, "status"):
        qry = qry.filter(getattr(Leave, "status") == "APPROVED")

    if q:
        if not joined_user:
            qry, _ = _with_user_join(qry, Leave, already_joined=False)
        qry = qry.filter(_q_user_filter(q))
        if _has_attr(Leave, "reason"):
            qry = qry.filter(or_(getattr(Leave, "reason").ilike(f"%{q}%")))

    rows = qry.order_by(order_col.desc()).limit(1000).all()

    def _days(lv):
        sc = getattr(lv, "start_date", getattr(lv, "from_date", None))
        ec = getattr(lv, "end_date",   getattr(lv, "to_date", None))
        return (ec - sc).days + 1 if sc and ec else None

    data = [{
        "id": lv.id,
        "user": _user_label(lv),
        "type": getattr(lv, "leave_type", "Congé"),
        "start": getattr(lv, "start_date", getattr(lv, "from_date", None)),
        "end": getattr(lv, "end_date",   getattr(lv, "to_date", None)),
        "days": _days(lv),
        "status": getattr(lv, "status", ""),
        "reason": getattr(lv, "reason", "") or getattr(lv, "note", "")
    } for lv in rows]

    return render_template("history/partials/leaves_table.html", items=data)
