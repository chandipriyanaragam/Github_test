import pytest
from fastapi.testclient import TestClient

from app import settings as settings_module
from app.start import app


@pytest.fixture
def client(tmp_path):
    original_db_path = settings_module.settings.db_path
    original_storage_dir = settings_module.settings.storage_dir
    object.__setattr__(settings_module.settings, "db_path", tmp_path / "test.db")
    object.__setattr__(settings_module.settings, "storage_dir", tmp_path / "documents")
    settings_module.settings.storage_dir.mkdir()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        object.__setattr__(settings_module.settings, "db_path", original_db_path)
        object.__setattr__(settings_module.settings, "storage_dir", original_storage_dir)
