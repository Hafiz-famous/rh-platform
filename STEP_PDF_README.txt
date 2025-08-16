
PDF Export (ReportLab)
======================

1) Installer la dépendance :
   pip install reportlab

2) Ajouter le blueprint dans app/routes/__init__.py :
   from .exports_pdf import bp as exports_pdf_bp
   ...
   app.register_blueprint(exports_pdf_bp)

3) Redémarrer l'app et ouvrir :
   /exports/report.pdf?month=YYYY-MM

Le PDF contient : KPIs mensuels, Top 3 "Employé du mois", tableau + barres de coûts par département.
