import os
from pathlib import Path

import pytest

TEST_DB = Path(__file__).with_name("test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["JTA_APP_ENV"] = "development"
os.environ["JTA_ADMIN_TOKEN"] = "test-token"
os.environ["JTA_DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["JTA_AUTO_SEED"] = "true"
os.environ["JTA_RATE_LIMIT_ENABLED"] = "false"  # Disable rate limiting in tests
os.environ["JTA_ENABLE_ADMIN_REVIEW"] = "true"  # Enable admin endpoints in tests
os.environ["JTA_ADMIN_REVIEW_TOKEN"] = "test-token"  # Set test token
# Enable JWT auth so Bearer tokens work in tests (the preferred auth path).
os.environ["JTA_JWT_AUTH_ENABLED"] = "true"
os.environ["JTA_JWT_SECRET_KEY"] = "test-jwt-secret-key-for-tests-only"
# Disable legacy shared-token admin path by default.
# Tests that specifically exercise the legacy token path must enable it locally
# (e.g. via monkeypatch or a pytest fixture that sets enable_legacy_admin_token=True).
os.environ["JTA_ENABLE_LEGACY_ADMIN_TOKEN"] = "false"
# Enforce JWT-only mutations in tests — matches production default.
# Tests that specifically exercise the legacy shared-token mutation path
# must monkeypatch get_settings or set JTA_ENABLE_LEGACY_ADMIN_TOKEN=true locally.
os.environ["JTA_ENFORCE_JWT_MUTATIONS"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.entities import *  # noqa: E402, F403 - Import all models to register with Base metadata
from app.seed.sample_data import seed_sample_data  # noqa: E402


Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_sample_data(db)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def jwt_admin_headers() -> dict:
    """Return Authorization headers with a valid JWT admin Bearer token.

    Use this fixture for any test that calls a mutation endpoint (admin_ingest,
    ingestion, ai_review process-source). Shared-token headers will be rejected
    by enforce_jwt_mutation_authority when JTA_ENFORCE_JWT_MUTATIONS=true.
    """
    from app.auth.jwt_handler import create_access_token
    token = create_access_token(email="test-admin@example.test", role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_session():
    with SessionLocal() as session:
        yield session
        session.rollback()
