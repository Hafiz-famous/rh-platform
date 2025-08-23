# Bundle de code — RH Platform (Sprints)

**Contenu**
- sprint-01-email-notifications/
  - Service d'envoi d'emails + templates + routes de congés (optionnel)
- sprint-02-dept-costs-backend/
  - API backend d'agrégation des coûts par département (mensuel)
- sprint-03-dept-costs-frontend/
  - Page Jinja + JS pour visualiser budgets vs réels (Chart.js)

**Intégration rapide**
1) Copiez les fichiers de chaque sprint dans votre projet `app/` aux mêmes chemins.
2) Dans `config.py`, ajoutez la configuration mail (voir Sprint 01 docs).
3) Dans `app/routes/__init__.py`, enregistrez le blueprint :
     from .costs import bp as costs_bp
     app.register_blueprint(costs_bp)
4) Placez vos identifiants SMTP dans `.env`. En dev, utilisez `MAIL_BACKEND=console`.
5) Redémarrez l'app. La page coûts est accessible sur `/costs`.
