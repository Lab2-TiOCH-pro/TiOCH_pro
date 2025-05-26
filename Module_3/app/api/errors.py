from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.exceptions import (
    BaseCustomException,
    DocumentNotFoundException,
    DatabaseException,
    ConflictException
)

# Ten plik definiuje globalne handlery wyjątków dla FastAPI.

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic's RequestValidationError."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Validation Error"},
    )

async def document_not_found_exception_handler(request: Request, exc: DocumentNotFoundException):
    """Handles DocumentNotFoundException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "message": "Resource Not Found"},
    )

async def database_exception_handler(request: Request, exc: DatabaseException):
    """Handles DatabaseException."""
    print(f"Database error occurred: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": "An internal database error occurred.", "message": "Database Error"},
    )


async def conflict_exception_handler(request: Request, exc: ConflictException):
    """Handles ConflictException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "message": "Operation Conflict"},
    )


async def generic_exception_handler(request: Request, exc: BaseCustomException):
    """Handles other custom exceptions derived from BaseCustomException."""
    print(f"Unhandled custom exception occurred: {type(exc).__name__} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "message": "Server Error"},
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles FastAPI's built-in HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handles any other unhandled exceptions as a last resort."""
    print(f"Unhandled exception occurred: {type(exc).__name__} - {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred.", "message": "Internal Server Error"},
    )
