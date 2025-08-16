
from app import create_app
from app.extensions import db
from app.models.department import Department
from app.models.user import User
from app.models.enums import Role

app = create_app()

with app.app_context():
    if not Department.query.first():
        it = Department(name="Informatique", code="IT")
        fin = Department(name="Finance", code="FIN")
        db.session.add_all([it, fin])
        db.session.commit()

    def ensure_user(email, first, last, role, dept_code, rate, pwd):
        u = User.query.filter_by(email=email).first()
        if u:
            return u
        dept = Department.query.filter_by(code=dept_code).first()
        u = User(email=email, first_name=first, last_name=last, role=role, department_id=dept.id, hourly_rate=rate)
        u.set_password(pwd)
        db.session.add(u)
        db.session.commit()
        return u

    ensure_user("admin@rh.local", "Admin", "Root", Role.ADMIN, "IT", 15.0, "admin123")
    ensure_user("manager@rh.local", "Mona", "Ger", Role.MANAGER, "FIN", 12.0, "manager123")
    ensure_user("emp@rh.local", "Sam", "Employe", Role.EMPLOYEE, "IT", 9.0, "emp123")

    print("Seed OK. Comptes:")
    print("  admin@rh.local / admin123")
    print("  manager@rh.local / manager123")
    print("  emp@rh.local / emp123")
