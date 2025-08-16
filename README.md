RH Platform

Plateforme de pointage et d’analyse RH pour la gestion du temps de travail et de la performance (Flask + SQLAlchemy + Bootstrap).

⚙️ Fonctionnalités

Authentification & rôles : Admin / Manager / Employé

Pointage : check-in / check-out, retards, géolocalisation, QR code sécurisé

Heures supplémentaires : création, suivi, validation

Congés : demande, validation, historique

Coûts salariaux : agrégation par département

Employé du mois : critères paramétrables (awards)

Tableaux de bord : global + modules (présence, heures sup, congés, coûts)

Exports : CSV et rapport PDF

(Optionnel) Workflow complet (audit) & Géorepérage (geofencing) – Sprint 8

🏗️ Stack

Backend : Python, Flask, Flask-Login, Flask-Migrate (Alembic), SQLAlchemy

DB : SQLite (par défaut) ou PostgreSQL

Frontend : Jinja2, HTML5, Bootstrap 5, JS

QR : qrcode

Email : SMTP (optionnel) rh-platform/
├─ app/
│  ├─ __init__.py
│  ├─ extensions.py
│  ├─ models/           # User, Department, Attendance, Leave, Overtime, ...
│  ├─ routes/           # auth, dashboard, attendance, admin, admin_users, ...
│  ├─ services/         # cost_service, mailer, security (token), ...
│  ├─ templates/        # base.html, auth/, admin/, dashboard/, ...
│  └─ static/           # css/, js/, images/
├─ migrations/          # Alembic
├─ seed.py              # création comptes de test / données de démo
├─ run.py               # lancement dev (optionnel, sinon 'flask run')
├─ requirements.txt
└─ README.md

Générer/Appliquer :
flask db migrate -m "sprint8 workflow audit geofence"
flask db upgrade
🧪 Tests
pytest -q
🩺 Dépannage (Windows)

psycopg2-binary échoue à compiler → utiliser psycopg 3 :
pip uninstall -y psycopg2-binary psycopg2
pip install "psycopg[binary]"
Alembic “revision not found / down_revision” : vérifier migrations/versions/.
En cas de base créée manuellement, on peut “stamper” l’état :
flask db stamp head
flask db migrate -m "rebuild"
flask db upgrade
Comptes de démo (seed)

admin@rh.local / admin123

manager@rh.local / manager123

emp@rh.local / emp123

Bonne utilisation ! 💙
