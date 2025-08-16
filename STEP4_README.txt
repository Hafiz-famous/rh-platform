
SPRINT 4 — Congés, Heures sup, QR sécurisé, Graphiques

1) Dépendances (si besoin) :
   pip install qrcode Pillow

2) Migrations :
   $env:FLASK_APP="app:create_app"
   # Recommandé : générer depuis ton code actuel
   flask --app app:create_app db migrate -m "leaves & overtime"
   flask --app app:create_app db upgrade
   # Ou utiliser le fichier fourni 0003_leaves_overtime.py en ajustant down_revision si nécessaire.

3) Lancer :
   python run.py

4) Tester :
   - /leaves/ (création + liste perso), /leaves/pending (validation)
   - /overtime/ (déclaration), /overtime/pending (validation)
   - /qr/attendance?action=checkin (PNG), puis /attendance/scan?token=... → Check-in
   - / (dashboard) → KPIs + 3 graphiques
