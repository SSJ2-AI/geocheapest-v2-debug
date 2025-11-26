import os
import sys

import pytest
import pytest_asyncio
from httpx import AsyncClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app, get_db  # noqa: E402
from database import MockFirestoreClient, _mock_db_data  # noqa: E402


@pytest.fixture
def mock_firestore():
    _mock_db_data.clear()
    return MockFirestoreClient()


@pytest_asyncio.fixture
async def client(mock_firestore):
    async def _get_mock_db():
        return mock_firestore

    app.dependency_overrides[get_db] = _get_mock_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides = {}
