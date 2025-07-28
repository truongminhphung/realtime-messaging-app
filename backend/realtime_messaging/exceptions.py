from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi import status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError



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

async def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors() if exc.errors() else str(exc)},
    )

async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI request validation errors (422 -> 400)."""
    errors = exc.errors()
    print(f"Request validation error: {errors}")  # Debugging line
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
            "detail": formatted_errors if len(formatted_errors) > 1 else formatted_errors[0] if formatted_errors else "Invalid request data"
        },
    )