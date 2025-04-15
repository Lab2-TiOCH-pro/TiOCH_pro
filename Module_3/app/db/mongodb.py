from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorGridFSBucket,
)
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MongoContext:
    """
    Class that stores the connection context to MongoDB (client, database, GridFS).
    Used as a global singleton to manage the connection.
    """

    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None
    fs: AsyncIOMotorGridFSBucket | None = None


db_context = MongoContext()


async def connect_to_mongo():
    """
    Establishes an asynchronous connection to MongoDB using the Engine.
    Initializes the client, database, and GridFS access.
    If the connection already exists, it does nothing.
    Called when a FastAPI application starts (lifespan).
    """
    if db_context.client:
        logger.info("MongoDB connection already established.")
        return
    logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
    try:
        db_context.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
        )
        db_context.db = db_context.client[settings.DATABASE_NAME]

        db_context.fs = AsyncIOMotorGridFSBucket(db_context.db)

        # Sprawdzenie połączenia
        await db_context.db.command("ping")
        logger.info(
            f"Successfully connected to MongoDB database '{settings.DATABASE_NAME}' and initialized GridFS."
        )
    except Exception as e:
        logger.error(f"Could not connect to MongoDB or initialize GridFS: {e}")

        db_context.client = None
        db_context.db = None
        db_context.fs = None
        raise RuntimeError(f"MongoDB connection failed: {e}")


async def close_mongo_connection():
    """
    Closes an asynchronous connection to MongoDB.
    Called when closing a FastAPI application (lifespan).
    """
    if db_context.client:
        logger.info("Closing MongoDB connection...")
        db_context.client.close()
        db_context.client = None
        db_context.db = None
        db_context.fs = None
        logger.info("MongoDB connection closed.")
    else:
        logger.info("MongoDB connection already closed or was never established.")


def get_db() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency function returning an instance of the Engine database.
    Used in other dependencies (e.g. for repository injection).
    Throws a fatal error if the database context is not initialized.
    """
    if db_context.db is None:

        logger.critical(
            "FATAL: get_db() called but database context is not initialized!"
        )
        raise RuntimeError("Database context is not initialized.")
    return db_context.db


def get_gridfs_bucket() -> AsyncIOMotorGridFSBucket:
    """
    FastAPI dependency function returning an AsyncIOMotorGridFSBucket instance.
    Used where direct access to GridFS is needed.
    Raises a fatal error if the GridFS context is not initialized.
    """
    if db_context.fs is None:
        logger.critical(
            "FATAL: get_gridfs_bucket() called but GridFS context is not initialized!"
        )
        raise RuntimeError("GridFS context is not initialized.")
    return db_context.fs
