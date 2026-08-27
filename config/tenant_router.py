"""
Router de Base de Données et Gestionnaire Multi-tenant pour FabOS.

Architecture :
- Base unique PostgreSQL avec un Schéma par Tenant (FabLab) via search_path (`tenant_<slug>, public`).
- En mode dev/local sans Postgres, bascule automatique sur un fichier SQLite par tenant.
- Modèles Master (FabLab, User, Group, Session, etc.) hébergés dans le schéma `public` (base `default`).
- Modèles Tenant (Equipment, Reservation, Workshop, Inventory, Project) hébergés dans le schéma du FabLab actif.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.backends.signals import connection_created
from django.dispatch import receiver

_thread_locals = threading.local()


@receiver(connection_created)
def _disable_sqlite_fk_for_tenants(sender, connection, **kwargs):
    """Optimise SQLite pour haute performance et désactive la contrainte FK stricte tenant -> master."""
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            if connection.alias != DEFAULT_DB_ALIAS:
                cursor.execute("PRAGMA foreign_keys = OFF;")


def set_current_tenant(tenant_slug: Optional[str]) -> None:
    """Active le slug du tenant courant dans le contexte du thread."""
    _thread_locals.tenant_slug = tenant_slug


def get_current_tenant() -> Optional[str]:
    """Récupère le slug du tenant actif pour le thread courant."""
    return getattr(_thread_locals, "tenant_slug", None)


def get_tenant_db_alias(tenant_slug: str) -> str:
    """Génère l'alias de connexion pour le slug d'un tenant."""
    clean_slug = tenant_slug.replace("-", "_")
    return f"tenant_{clean_slug}"


def tenant_schema_name(tenant_slug: str) -> str:
    """Génère le nom du schéma PostgreSQL d'un tenant."""
    return "tenant_" + tenant_slug.replace("-", "_")


def _is_postgres_default() -> bool:
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    return "postgresql" in engine or "postgres" in engine


_ensured_schemas: set[str] = set()


def _ensure_pg_schema(schema: str) -> None:
    """Crée le schéma Postgres s'il n'existe pas encore."""
    if schema in _ensured_schemas:
        return
    conn = connections[DEFAULT_DB_ALIAS]
    with conn.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    _ensured_schemas.add(schema)


def ensure_tenant_db_registered(tenant_slug: str, db_path: Optional[str] = None) -> str:
    import sys
    if "test" in sys.argv or getattr(settings, "IS_TESTING", False):
        return DEFAULT_DB_ALIAS

    alias = get_tenant_db_alias(tenant_slug)
    if alias in settings.DATABASES:
        return alias

    default_cfg = settings.DATABASES.get("default", {})

    if _is_postgres_default():
        schema = tenant_schema_name(tenant_slug)
        cfg = dict(default_cfg)
        options = dict(default_cfg.get("OPTIONS", {}))
        options["options"] = f"-c search_path={schema},public"
        cfg["OPTIONS"] = options
        cfg["CONN_MAX_AGE"] = 60
        settings.DATABASES[alias] = cfg
        _ensure_pg_schema(schema)
        return alias

    # Fallback SQLite local
    if not db_path:
        tenant_dir = Path(settings.MEDIA_ROOT) / "tenants" / tenant_slug
        tenant_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(tenant_dir / "db.sqlite3")

    base_config = dict(default_cfg)
    base_config.update({
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": db_path,
        "ATOMIC_REQUESTS": True,
        "TIME_ZONE": getattr(settings, "TIME_ZONE", None),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {},
        "AUTOCOMMIT": True,
    })

    settings.DATABASES[alias] = base_config
    return alias


def migrate_tenant(tenant_slug: str, verbosity: int = 0) -> str:
    """Provisionne et exécute les migrations pour un tenant donné."""
    from django.core.management import call_command

    alias = ensure_tenant_db_registered(tenant_slug)
    if _is_postgres_default():
        schema = tenant_schema_name(tenant_slug)
        conn = connections[DEFAULT_DB_ALIAS]
        with conn.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            cursor.execute(
                f'CREATE TABLE IF NOT EXISTS "{schema}".django_migrations '
                f"(LIKE public.django_migrations INCLUDING ALL)"
            )
    call_command("migrate", database=alias, interactive=False, verbosity=verbosity)
    return alias


class TenantRouter:
    """Router Django pour le partitionnement multi-tenant."""

    MASTER_MODELS = {
        "fablab",
        "user",
        "group",
        "permission",
        "contenttype",
        "session",
        "logentry",
        "subscription",
    }

    def db_for_read(self, model, **hints) -> Optional[str]:
        import sys
        if "test" in sys.argv or getattr(settings, "IS_TESTING", False):
            return DEFAULT_DB_ALIAS

        model_name = model._meta.model_name.lower()
        if model_name in self.MASTER_MODELS:
            return DEFAULT_DB_ALIAS

        tenant_slug = get_current_tenant()
        if tenant_slug:
            return ensure_tenant_db_registered(tenant_slug)
        return DEFAULT_DB_ALIAS

    def db_for_write(self, model, **hints) -> Optional[str]:
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints) -> Optional[bool]:
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints) -> Optional[bool]:
        if db == DEFAULT_DB_ALIAS:
            return True
        engine = settings.DATABASES.get(db, {}).get("ENGINE", "")
        if "postgresql" in engine or "postgres" in engine:
            is_master = (model_name or "").lower() in self.MASTER_MODELS
            return not is_master
        return True
