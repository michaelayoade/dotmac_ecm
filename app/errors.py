from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _error_payload(code: str, message: str, details):
    return {"code": code, "message": message, "details": details}


def register_error_handlers(app) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail
        code = f"http_{exc.status_code}"
        message = "Request failed"
        details = None
        if isinstance(detail, dict):
            code = detail.get("code", code)
            message = detail.get("message", message)
            details = detail.get("details")
        elif isinstance(detail, str):
            message = detail
        else:
            details = detail
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code, message, details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        # exc.errors() ctx may contain raw Exception objects (not JSON-serialisable).
        # Sanitise by converting each error to string-safe form.
        errors = [
            {k: str(v) if k == "ctx" else v for k, v in err.items()}
            for err in exc.errors(include_url=False)
        ]
        return JSONResponse(
            status_code=422,
            content=_error_payload("validation_error", "Validation error", errors),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=_error_payload("internal_error", "Internal server error", None),
        )
