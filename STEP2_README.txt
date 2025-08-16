
SPRINT 2 — Base de données + migrations

1) Met à jour .env :
   DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/rh_platform

2) Variables d'environnement pour Flask CLI (PowerShell) :
   $env:FLASK_APP="run.py"

3) Applique les migrations :
   flask db upgrade

4) Seed (données de base) :
   python seed.py

5) Lance l'app :
   python run.py
