
SPRINT 5 — Employé du mois, Exports CSV, Dashboard, Tests

1) Migrations :
   $env:FLASK_APP="app:create_app"
   flask --app app:create_app db migrate -m "awards & settings"
   flask --app app:create_app db upgrade

2) Utilisation :
   - /admin/awards : pondérations, top 10, enregistrer gagnant
   - /api/awards/current : JSON gagnant pour le mois
   - /exports/*.csv : exports

3) Tests :
   pip install pytest
   pytest -q
