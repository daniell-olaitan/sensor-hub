import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="function", autouse=True)
def reset_redis():
    """Reset Redis state before each test."""
    import subprocess

    try:
        subprocess.run(["redis-cli", "FLUSHALL"], capture_output=True, timeout=2)
    except Exception:
        pass

    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unique_id():
    return uuid.uuid4().hex[:8]
