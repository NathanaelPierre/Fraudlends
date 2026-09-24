"""
Tiny, targeted startup migration — not a full Alembic history.

`Base.metadata.create_all()` (called in main.py) only creates tables
that don't exist yet; it never alters an existing table. This project
already ships a populated `fraudlens.db` with a `users` table that
predates the `role` / `is_active` columns added for the admin
dashboard, so a plain create_all silently leaves those columns
missing and every request that touches them breaks with a "no such
column" error at query time. The same problem applies on Postgres
(e.g. Neon): the `checks` table gained sender_auto_detected,
sender_detection_source_text, detected_language,
registry_status_detail, and evidence_detail after the table was
first created there, and an existing deployed table doesn't grow
those columns on its own.

`run_startup_migrations` is idempotent (checks column existence
before adding) and safe to call on every boot, for both SQLite and
Postgres. It also bootstraps exactly one admin the first time it
runs, so there's a way into /admin without hand-editing the database:
the earliest-registered account is promoted automatically if no admin
exists yet. After that, admins manage further promotions themselves
from the admin panel (POST /admin/users/{id}/role) — see RUNNING.md.
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine


def _existing_columns_sqlite(engine: Engine, table: str) -> set:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _existing_columns_postgres(engine: Engine, table: str) -> set:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :table"
            ),
            {"table": table},
        ).fetchall()
    return {row[0] for row in rows}


def run_startup_migrations(engine: Engine) -> None:
    if engine.url.get_backend_name().startswith("sqlite"):
        _run_sqlite_migrations(engine)
    else:
        _run_postgres_migrations(engine)

    _bootstrap_first_admin(engine)


def _run_sqlite_migrations(engine: Engine) -> None:
    columns = _existing_columns_sqlite(engine, "users")
    statements = []
    if "role" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN role VARCHAR NOT NULL DEFAULT 'user'")
    if "is_active" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")

    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))


def _run_postgres_migrations(engine: Engine) -> None:
    statements = []

    # users table: same role/is_active patch as SQLite, in case an
    # early Postgres deploy predates these columns too.
    user_columns = _existing_columns_postgres(engine, "users")
    if user_columns:
        if "role" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR NOT NULL DEFAULT 'user'")
        if "is_active" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")

    # checks table: columns added for sender auto-detection, language
    # detection, registry status detail, and structured evidence —
    # see models.py's Check class for the full explanation of each.
    check_columns = _existing_columns_postgres(engine, "checks")
    if check_columns:
        check_patches = {
            "sender_auto_detected": "BOOLEAN NOT NULL DEFAULT FALSE",
            "sender_detection_source_text": "VARCHAR",
            "detected_language": "VARCHAR NOT NULL DEFAULT 'en'",
            "registry_status_detail": "VARCHAR",
            "evidence_detail": "JSON",
        }
        for col, coltype in check_patches.items():
            if col not in check_columns:
                statements.append(f"ALTER TABLE checks ADD COLUMN IF NOT EXISTS {col} {coltype}")

    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))


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
