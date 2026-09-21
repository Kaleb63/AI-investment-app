import os
import tempfile
from pathlib import Path

import pytest

TEST_DATABASE_PATH = Path(tempfile.gettempdir()) / (f"ai-investment-tests-{os.getpid()}.sqlite3")
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"
os.environ["SECRET_KEY"] = "tests-only-secret-key-with-at-least-32-bytes"


@pytest.fixture(scope="session", autouse=True)
def clean_test_database():
    yield
    from backend.database import engine

    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)
