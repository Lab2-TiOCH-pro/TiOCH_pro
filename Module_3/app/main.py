from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging

from app.api.endpoints import documents
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.api.errors import (
    conflict_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    document_not_found_exception_handler,
    generic_exception_handler,
)

from app.core.exceptions import (
    BaseCustomException,
    ConflictException,
    DocumentNotFoundException,
    DatabaseException,
    FileNotFoundInGridFSException,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager to handle startup and shutdown events."""
    logger.info("Application startup...")
    try:
        await connect_to_mongo()
        yield
    except Exception as e:
        logger.critical(f"Application startup failed due to MongoDB connection error: {e}")

    finally:
        logger.info("Application shutdown sequence initiated...")
        await close_mongo_connection()
        logger.info("Application shutdown sequence complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for managing documents, conversion, sensitive data identification.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_exception_handler(FileNotFoundInGridFSException, document_not_found_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(DocumentNotFoundException, document_not_found_exception_handler)
app.add_exception_handler(DatabaseException, database_exception_handler)
app.add_exception_handler(ConflictException, conflict_exception_handler) 
app.add_exception_handler(BaseCustomException, generic_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["Documents"])


@app.get(
    "/",
    tags=["Root"],
    summary="Root Endpoint / Health Check",
    description="Returns a welcome message indicating the service is running.",
)
async def read_root():
    """Returns a simple welcome message indicating the service is running."""
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}
