"""
Shared pytest fixtures. Each test gets its own isolated in-memory
SQLite database, and the shared app.database module's engine/session
are patched once, before app.main is imported, so main.py's own
create_all() targets the same test database the fixtures use.
"""
import os
import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("ENCRYPTION_KEY", "6cXwXqzXG3v3B0y3aM6Q4h9dK1jL8pWnR5tUvYz2Abc=")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database_module

_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
database_module.engine = _test_engine
database_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def _reset_database():
    Base.metadata.drop_all(bind=_test_engine)
    Base.metadata.create_all(bind=_test_engine)
    yield


@pytest.fixture()
def db_session():
    session = database_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_as_real_http(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    def _make(email="testuser@fraudlens.mu", password="testpass123"):
        client.post("/auth/signup", json={"email": email, "password": password})
        r = client.post("/auth/login", data={"username": email, "password": password})
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
