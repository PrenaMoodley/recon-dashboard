import os
import tempfile

# Must be set before the app is imported: the engine is created at import time.
# CI sets DATABASE_URL to a PostgreSQL service; locally we use a temporary SQLite file.
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/recon_test.db")
os.environ["WEBHOOK_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture
def client():
    seed()  # fresh tables and invoices for every test
    with TestClient(app) as c:
        yield c
