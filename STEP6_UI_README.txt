
SPRINT 6 — UI/UX polish (Bootstrap 5 + dark mode + skeletons)
-------------------------------------------------------------

Fichiers à copier par-dessus ton projet :
- app/templates/base.html
- app/templates/dashboard/index.html
- app/templates/attendance/scan.html
- app/static/css/style.css
- app/static/js/main.js
- app/static/js/dashboard.js
- app/static/js/attendance.js
- app/static/images/favicon.png

Points clés :
- Navbar améliorée + indicateur de page active
- Thème clair/sombre (persisté dans localStorage) via bouton en haut à droite
- Cartes "soft" (coins arrondis, ombres) + squelettes de chargement
- Cartes KPI + actions rapides (pointer, QR, PDF)
- Charts Chart.js responsives
- Toasts Bootstrap pour retours utilisateur

Aucune migration, aucune dépendance supplémentaire.
