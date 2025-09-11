import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi import status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


logger = logging.getLogger(__name__)


def configure_error_handlers(app: FastAPI) -> None:
    """Configure custom error handlers for the application."""

    app.add_exception_handler(ValueError, handle_invalid_data_error)
    app.add_exception_handler(ValidationError, handle_validation_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)


async def handle_invalid_data_error(request: Request, exc: ValueError) -> JSONResponse:
    """Handle invalid data errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


async def handle_validation_error(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors() if exc.errors() else str(exc)},
    )


async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request validation errors (422 -> 400)."""
    errors = exc.errors()
    logger.error(f"Request validation error: {errors}")
    formatted_errors = []

    for error in errors:
        error_msg = error.get("msg", "Validation error")
        field_name = " -> ".join(str(loc) for loc in error.get("loc", []))

        if field_name:
            formatted_errors.append(f"{field_name}: {error_msg}")
        else:
            formatted_errors.append(error_msg)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": (
                formatted_errors
                if len(formatted_errors) > 1
                else formatted_errors[0] if formatted_errors else "Invalid request data"
            )
        },
    )


class DBItemExistsError(HTTPException):
    """Custom exception for item already exists."""

    def __init__(self, detail: str = "Item already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class InternalServerError(HTTPException):
    """Custom exception for internal server errors."""

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class NotFoundError(HTTPException):
    """Custom exception for not found errors."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedError(HTTPException):
    """Custom exception for unauthorized access."""

    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenError(HTTPException):
    """Custom exception for forbidden access."""

    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
