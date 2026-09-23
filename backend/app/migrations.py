"""
Tiny, targeted startup migration — not a full Alembic history.

`Base.metadata.create_all()` (called in main.py) only creates tables
that don't exist yet; it never alters an existing table. This project
already ships a populated `fraudlens.db` with a `users` table that
predates the `role` / `is_active` columns added for the admin
dashboard, so a plain create_all silently leaves those columns
missing and every request that touches them breaks with a "no such
column" error at query time.

`run_startup_migrations` is idempotent (checks column existence via
PRAGMA before adding) and safe to call on every boot. It also
bootstraps exactly one admin the first time it runs, so there's a way
into /admin without hand-editing the database: the earliest-registered
account is promoted automatically if no admin exists yet. After that,
admins manage further promotions themselves from the admin panel
(POST /admin/users/{id}/role) — see RUNNING.md.
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine


def _existing_columns(engine: Engine, table: str) -> set:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def run_startup_migrations(engine: Engine) -> None:
    if not engine.url.get_backend_name().startswith("sqlite"):
        # Non-SQLite deployments should use a real Alembic migration
        # instead of this ad hoc PRAGMA-based patch.
        return

    columns = _existing_columns(engine, "users")
    statements = []
    if "role" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN role VARCHAR NOT NULL DEFAULT 'user'")
    if "is_active" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")

    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))

    _bootstrap_first_admin(engine)


def _bootstrap_first_admin(engine: Engine) -> None:
    with engine.begin() as conn:
        existing_admin = conn.execute(
            text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        ).fetchone()
        if existing_admin:
            return

        earliest = conn.execute(
            text("SELECT id FROM users ORDER BY id ASC LIMIT 1")
        ).fetchone()
        if earliest:
            conn.execute(
                text("UPDATE users SET role = 'admin' WHERE id = :id"),
                {"id": earliest[0]},
            )
