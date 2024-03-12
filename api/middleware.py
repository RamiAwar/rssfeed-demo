import logging
from typing import Awaitable, Callable

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class JSONErrorResponse(JSONResponse):
    def __init__(
        self,
        error: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        self.error = error
        self.message = message
        super().__init__(
            status_code=status_code, content={"error": error, "message": message}
        )


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle different exceptions and return a standardized JSON response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> JSONResponse | Response:
        try:
            return await call_next(request)

        # Handle validation errors
        except ValidationError as validation_error:
            return JSONErrorResponse(
                error="validation_error",
                message=str(validation_error.message),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Handle resource not found errors
        except NotFoundError as not_found_error:
            return JSONErrorResponse(
                error="not_found",
                message=str(not_found_error.message),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Handle unknown error types coming from FastAPI
        except HTTPException as http_exception:
            return JSONErrorResponse(
                error="http_exception",
                message=str(http_exception.detail),
                status_code=http_exception.status_code,
            )

        # Handle internal server errors that shouldn't be exposed to the user
        except Exception as e:
            logger.exception(msg=e.__class__.__name__, args=e.args)
            return JSONErrorResponse(
                error="internal_server_error",
                message="Unexpected error occurred.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
