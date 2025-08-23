# Sprint 02 — Backend coûts par départements

## Fichiers à copier
- `app/services/costs_service.py`
- `app/routes/costs.py`

## Intégration
- Dans `app/routes/__init__.py`, enregistrer le blueprint :
    from .costs import bp as costs_bp
    app.register_blueprint(costs_bp)

## Hypothèses
- Si la table `payslips` existe avec l'un des schémas suivants, les coûts réels seront agrégés automatiquement :
    * (department_id, period, net_amount)
    * (department_id, period_month, total_net)
  Sinon, seules les lignes budgétaires seront affichées (budget_monthly + overhead à 0).

## Appels REST
- GET `/costs/api/summary?period=YYYY-MM`
