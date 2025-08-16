
SPRINT 3 — Auth, rôles, pointage check-in/out, admin basique

1) Installer dépendances (si besoin) :
   pip install Flask-Login

2) Variables pour Flask CLI (PowerShell) :
   $env:FLASK_APP="app:create_app"

3) Appliquer la migration 0002 (Attendance) :
   flask --app app:create_app db upgrade

4) Lancer l'app :
   python run.py

5) Se connecter :
   - admin@rh.local / admin123
   - manager@rh.local / manager123
   - emp@rh.local / emp123

6) Tester :
   - /auth/login  → connexion
   - /            → dashboard avec stats
   - /attendance/scan → boutons Check-in / Check-out
   - /admin/      → accessible uniquement ADMIN (liste des utilisateurs)
