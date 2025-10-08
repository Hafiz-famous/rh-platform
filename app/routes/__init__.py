from __future__ import annotations

import os
import types
import typing as t
import importlib
import pkgutil
import traceback

from flask import Flask, Blueprint

BlueprintLike = t.Union[Blueprint, t.Iterable[Blueprint]]


def _coerce_list(env_value: str | None) -> list[str]:
    if not env_value:
        return []
    return [x.strip() for x in env_value.split(",") if x.strip()]


def _import_module(mod_path: str) -> types.ModuleType:
    return importlib.import_module(mod_path)


def _extract_blueprints(mod: types.ModuleType, app: Flask) -> list[Blueprint]:
    """
    Récupère 0..n blueprints exposés par un module.
    Conventions supportées :
      - mod.bp : Blueprint
      - mod.blueprints : Iterable[Blueprint]
      - mod.get_blueprint([app]) -> Blueprint | Iterable[Blueprint]
      - mod.create_blueprint([app]) -> Blueprint | Iterable[Blueprint]
    """
    found: list[Blueprint] = []

    def _extend(obj: BlueprintLike | None) -> None:
        if obj is None:
            return
        if isinstance(obj, Blueprint):
            found.append(obj)
            return
        # Iterable de blueprints
        try:
            for bp in obj:  # type: ignore[assignment]
                if isinstance(bp, Blueprint):
                    found.append(bp)
        except TypeError:
            pass

    # Attributs directs
    if hasattr(mod, "bp"):
        _extend(getattr(mod, "bp"))

    if hasattr(mod, "blueprints"):
        _extend(getattr(mod, "blueprints"))

    # Fabriques éventuelles
    for factory_name in ("get_blueprint", "create_blueprint"):
        if hasattr(mod, factory_name):
            factory = getattr(mod, factory_name)
            try:
                try:
                    _extend(factory(app))  # avec app
                except TypeError:
                    _extend(factory())     # sans app
            except Exception:
                app.logger.debug(
                    "Échec %s() sur %s\n%s",
                    factory_name, mod.__name__, traceback.format_exc()
                )

    # Dédupli
    uniq: dict[str, Blueprint] = {}
    for bp in found:
        uniq.setdefault(bp.name, bp)
    return list(uniq.values())


def _register_module(
    app: Flask,
    package: str,
    module: str,
    *,
    required: bool,
    seen_bp_names: set[str]
) -> None:
    """Importe package.module, trouve ses blueprints et les enregistre."""
    mod_path = f"{package}.{module}"
    try:
        mod = _import_module(mod_path)
        bps = _extract_blueprints(mod, app)
        if not bps:
            raise AttributeError(f"{mod_path} n'expose pas de blueprint ('bp' ou équivalent)")

        for bp in bps:
            if bp.name in seen_bp_names or bp.name in app.blueprints:
                app.logger.debug("Blueprint déjà enregistré (ignoré): %s", bp.name)
                continue
            app.register_blueprint(bp)
            seen_bp_names.add(bp.name)
            app.logger.debug("Blueprint chargé: %s -> %s", mod_path, bp.name)

    except Exception as e:
        msg = f"Blueprint non enregistré ({mod_path}): {e}"
        if required:
            app.logger.error("%s\n%s", msg, traceback.format_exc())
            raise
        else:
            app.logger.debug("%s", msg)


def _autodiscover_modules(app: Flask, package: str) -> list[str]:
    """Retourne la liste des sous-modules trouvés dans 'package' (sans privés)."""
    try:
        pkg = importlib.import_module(package)
        if not hasattr(pkg, "__path__"):
            return []
        names: list[str] = []
        for m in pkgutil.iter_modules(pkg.__path__):  # type: ignore[arg-type]
            name = m.name
            if not name.startswith("_"):
                names.append(name)
        return names
    except Exception:
        app.logger.debug("Auto-discovery ignoré pour %s\n%s", package, traceback.format_exc())
        return []


def register_blueprints(app: Flask) -> None:
    """
    Enregistre tous les blueprints.
    - 'required' lève si manquants/invalides
    - 'optional' log et continue
    - ROUTES_DISABLE="a,b" pour ignorer certains modules
    - ROUTES_REQUIRED / ROUTES_OPTIONAL (CSV) pour surcharger les listes
    - ROUTES_AUTODISCOVER=1 pour ajouter automatiquement les sous-modules restants
    """
    package = __package__ or "app.routes"  # "app.routes"

    # Listes par défaut
    required = [
        "auth",
        "dashboard",
        "attendance",
        "admin",
        "api",
        "leaves",
        "overtime",
        "qr",
        "awards",
        "exports",
        "history",        # ← AJOUT : pour que /history/ existe
    ]
    optional = [
        "admin_users",
        "api_awards",
        "workflow",
        "admin_geofence",
        "exports_pdf",    # laissé en optionnel si tu gardes ce module
    ]

    # Surcharges env
    env_required = _coerce_list(os.getenv("ROUTES_REQUIRED"))
    env_optional = _coerce_list(os.getenv("ROUTES_OPTIONAL"))
    if env_required:
        required = env_required
    if env_optional:
        optional = env_optional

    # Désactivation explicite
    disabled = set(_coerce_list(os.getenv("ROUTES_DISABLE")))
    if disabled:
        required = [m for m in required if m not in disabled]
        optional = [m for m in optional if m not in disabled]

    seen_bp_names: set[str] = set(app.blueprints.keys())

    # Requis
    for m in required:
        _register_module(app, package, m, required=True, seen_bp_names=seen_bp_names)

    # Optionnels connus
    for m in optional:
        _register_module(app, package, m, required=False, seen_bp_names=seen_bp_names)

    # Auto-discovery (facultatif)
    if os.getenv("ROUTES_AUTODISCOVER", "0").lower() in ("1", "true"):
        known = set(required) | set(optional) | disabled
        discovered = _autodiscover_modules(app, package)
        for m in discovered:
            if m in known:
                continue
            _register_module(app, package, m, required=False, seen_bp_names=seen_bp_names)

    app.logger.debug(
        "Blueprints enregistrés: %s",
        ", ".join(sorted(seen_bp_names)) or "aucun"
    )
