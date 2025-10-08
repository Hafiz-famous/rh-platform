# Sprint — HISTORIQUE RH (Pointages, Heures sup, Congés)

## 1) Copier les fichiers
Copie le contenu de `app/` dans ton projet existant `app/` :
- `app/routes/history.py`
- `app/templates/history/index.html`

## 2) Enregistrer le blueprint
Ouvre `app/routes/__init__.py` et ajoute `"history"` à la liste des optionnels (ou requis) :

```python
optional = [
    "admin_users",
    "api_awards",
    "workflow",
    "admin_geofence",
    "exports_pdf",
    "history",  # <-- ajouté
]
```

(Alternative : applique `patch/routes_init.diff`)

## 3) Rôles & accès
Les routes exigent `@roles_required(Role.ADMIN, Role.HR)`.
- Si tu **n’as pas** `Role.HR`, remplace par `@roles_required(Role.ADMIN)` dans `history.py` (3 occurrences).

## 4) CSP (nonce)
Le template utilise `<script nonce="{{ csp_nonce }}">`. 
Si tu as déjà mis en place le nonce dans `after_request`, c’est bon.
Sinon, ajoute la génération d’un nonce et le header `Content-Security-Policy` (voir tes snippets existants).

## 5) Navigation (optionnel)
Ajoute un lien dans ta navbar pour ADMIN/RH uniquement :

```
{% if current_user.is_authenticated and (current_user.has_role('ADMIN') or current_user.has_role('HR')) %}
  <li class="nav-item"><a class="nav-link" href="{{ url_for('history.index') }}">Historique</a></li>
{% endif %}
```

## 6) Migrations
Aucune migration requise. On lit les modèles existants (Overtime, Punch, Leave).

## 7) Indices (performance)
Recommandé en prod si beaucoup d’historique :
- Overtime(user_id, work_date), Overtime(status), Overtime(source/origin)
- Punch(user_id, check_in)
- Leave(user_id, start_date), Leave(end_date), Leave(status)

## 8) Lancement
Enregistre, puis relance `python run.py` (ou laisse le reloader).
Accède à `/history/` connecté en ADMIN/RH.
