# Sprint 01 — Notifications email

## Fichiers à copier
- `app/services/email_service.py`
- `app/templates/email/leave_submitted.html`
- `app/templates/email/leave_status.html`
- (Optionnel) Remplacer `app/routes/leaves.py` par la version fournie si vous voulez
  l'appel à `update_status(..., actor_user_id=...)` et la gestion robuste.

## Config
- Dans `config.py` (classe `Config`) ajoutez les variables de mail (voir `docs/config_mail_snippet.txt`).
- Ajoutez dans `.env` vos identifiants SMTP (voir `.env.example.mail`). En dev, utilisez `MAIL_BACKEND=console`.

## Dépendance
- `pip install Flask-Mailman>=1.1.0` (déjà configuré dans `app/extensions.py` via `mail = Mail()`).
