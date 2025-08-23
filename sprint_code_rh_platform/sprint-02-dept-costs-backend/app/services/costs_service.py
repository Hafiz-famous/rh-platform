# app/services/costs_service.py
from __future__ import annotations

from datetime import date
from typing import Dict, Any
from sqlalchemy import text, inspect
from ..extensions import db
from ..models.department import Department

def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1).isoformat()
    # naive end (next month first day); SQLite BETWEEN is inclusive so we use < next
    if month == 12:
        end = date(year + 1, 1, 1).isoformat()
    else:
        end = date(year, month + 1, 1).isoformat()
    return start, end

def _has_table(name: str) -> bool:
    return inspect(db.engine).has_table(name)

def _columns(table: str) -> set[str]:
    # SQLite pragma; works fine for quick reflection
    rows = db.session.execute(text(f"PRAGMA table_info({table})")).mappings().all()
    return {r["name"] for r in rows}

def summarize_month(year: int, month: int) -> Dict[str, Any]:
    """Return costs summary per department for a given period.
    Tries to use `payslips` if available; otherwise returns budgets only.
    """
    start, end = _month_bounds(year, month)

    # base: departments
    depts = db.session.query(Department).filter(Department.is_active.is_(True)).all()

    # Try payslips table
    actuals_by_dept: dict[int, float] = {}
    if _has_table("payslips"):
        cols = _columns("payslips")
        # Try a few common schemas
        if {"department_id", "period", "net_amount"} <= cols:
            q = text("""
                SELECT department_id AS did, COALESCE(SUM(net_amount),0) AS total
                FROM payslips
                WHERE period >= :start AND period < :end
                GROUP BY department_id
            """)
            rows = db.session.execute(q, {"start": start, "end": end}).all()
            actuals_by_dept = {int(d): float(t) for d, t in rows}
        elif {"department_id", "period_month", "total_net"} <= cols:
            q = text("""
                SELECT department_id AS did, COALESCE(SUM(total_net),0) AS total
                FROM payslips
                WHERE period_month >= :start AND period_month < :end
                GROUP BY department_id
            """)
            rows = db.session.execute(q, {"start": start, "end": end}).all()
            actuals_by_dept = {int(d): float(t) for d, t in rows}
        # else: unknown schema -> leave actuals_by_dept empty

    data = []
    tot_budget = tot_actual = 0.0
    for d in depts:
        budget = float(getattr(d, "budget_monthly", 0) or 0)
        actual = float(actuals_by_dept.get(d.id, 0.0))
        overhead_rate = float(getattr(d, "overhead_rate", 0) or 0)
        overhead = round(actual * (overhead_rate / 100.0), 2)
        actual_with_overhead = round(actual + overhead, 2)

        data.append({
            "department_id": d.id,
            "code": d.code,
            "name": d.name,
            "currency": getattr(d, "currency", "XOF"),
            "budget_monthly": budget,
            "actual": actual,
            "overhead_rate": overhead_rate,
            "actual_with_overhead": actual_with_overhead,
            "variance": round(budget - actual_with_overhead, 2),
        })
        tot_budget += budget
        tot_actual += actual_with_overhead

    return {
        "period": f"{year:04d}-{month:02d}",
        "total_budget": round(tot_budget, 2),
        "total_actual": round(tot_actual, 2),
        "rows": data,
    }
