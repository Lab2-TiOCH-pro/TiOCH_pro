import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import mongodb
from app.core.config import settings

@pytest.mark.asyncio
@patch('app.db.mongodb.AsyncIOMotorGridFSBucket', new_callable=MagicMock)
@patch('app.db.mongodb.AsyncIOMotorClient', new_callable=MagicMock)
async def test_connect_to_mongo_success(MockMotorClient: MagicMock, MockGridFSBucket: MagicMock):
    """Testuje pomyślne połączenie z MongoDB."""
    mock_client_instance = AsyncMock()
    mock_db_instance = AsyncMock()
    mock_fs_instance = AsyncMock()

    MockMotorClient.return_value = mock_client_instance
    mock_client_instance.__getitem__.return_value = mock_db_instance
    MockGridFSBucket.return_value = mock_fs_instance

    mock_db_instance.command = AsyncMock(return_value={"ok": 1})

    mongodb.db_context.client = None
    mongodb.db_context.db = None
    mongodb.db_context.fs = None

    await mongodb.connect_to_mongo()

    MockMotorClient.assert_called_once_with(settings.MONGODB_URL)
    mock_client_instance.__getitem__.assert_called_once_with(settings.DATABASE_NAME)
    MockGridFSBucket.assert_called_once_with(mock_db_instance)
    mock_db_instance.command.assert_awaited_once_with("ping")

    assert mongodb.db_context.client == mock_client_instance
    assert mongodb.db_context.db == mock_db_instance
    assert mongodb.db_context.fs == mock_fs_instance

    mongodb.db_context.client = None
    mongodb.db_context.db = None
    mongodb.db_context.fs = None


@pytest.mark.asyncio
@patch('app.db.mongodb.AsyncIOMotorGridFSBucket', new_callable=MagicMock)
@patch('app.db.mongodb.AsyncIOMotorClient', new_callable=MagicMock)
async def test_connect_to_mongo_failure_ping(MockMotorClient: MagicMock, MockGridFSBucket: MagicMock):
    """Testuje błąd połączenia podczas pingowania."""

    mock_client_instance = AsyncMock()

    mock_db_instance = AsyncMock(spec=AsyncIOMotorDatabase)
    mock_fs_instance = AsyncMock()

    MockMotorClient.return_value = mock_client_instance
    mock_client_instance.__getitem__.return_value = mock_db_instance

    MockGridFSBucket.return_value = mock_fs_instance

    mock_db_instance.command = AsyncMock(side_effect=Exception("Ping failed!"))

    mongodb.db_context.client = None
    mongodb.db_context.db = None
    mongodb.db_context.fs = None

    with pytest.raises(RuntimeError, match="MongoDB connection failed: Ping failed!"):
        await mongodb.connect_to_mongo()

    MockGridFSBucket.assert_called_once_with(mock_db_instance)
    mock_db_instance.command.assert_awaited_once_with("ping")

    assert mongodb.db_context.client is None
    assert mongodb.db_context.db is None
    assert mongodb.db_context.fs is None

@pytest.mark.asyncio
async def test_close_mongo_connection_already_closed():
    """Testuje próbę zamknięcia, gdy połączenie jest już zamknięte."""
    mongodb.db_context.client = None
    mongodb.db_context.db = None
    mongodb.db_context.fs = None


    await mongodb.close_mongo_connection()

    assert mongodb.db_context.client is None


def test_get_db_success():
    """Testuje pobranie instancji bazy, gdy kontekst jest ustawiony."""

    mock_db = MagicMock()
    mongodb.db_context.db = mock_db
    mongodb.db_context.client = MagicMock()

    db_instance = mongodb.get_db()

    assert db_instance == mock_db

    mongodb.db_context.client = None
    mongodb.db_context.db = None


def test_get_db_not_initialized():
    """Testuje pobranie instancji bazy, gdy kontekst jest pusty."""
    mongodb.db_context.db = None

    with pytest.raises(RuntimeError, match="Database context is not initialized."):
        mongodb.get_db()


def test_get_gridfs_bucket_success():
    """Testuje pobranie instancji GridFS, gdy kontekst jest ustawiony."""
    mock_fs = MagicMock()
    mongodb.db_context.fs = mock_fs
    mongodb.db_context.client = MagicMock()

    fs_instance = mongodb.get_gridfs_bucket()

    assert fs_instance == mock_fs

    mongodb.db_context.client = None
    mongodb.db_context.fs = None


def test_get_gridfs_bucket_not_initialized():
    """Testuje pobranie instancji GridFS, gdy kontekst jest pusty."""
    mongodb.db_context.fs = None

    with pytest.raises(RuntimeError, match="GridFS context is not initialized."):
        mongodb.get_gridfs_bucket()