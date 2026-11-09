import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DomainError(Exception):
    status_code = 500
    code = "domain_error"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class InvalidFileError(DomainError):
    status_code = 422
    code = "invalid_file"


class FileTooLargeError(DomainError):
    status_code = 413
    code = "file_too_large"


class InvalidInputError(DomainError):
    status_code = 422
    code = "validation_error"


class DuplicateReportError(ConflictError):
    code = "reporte_duplicado"


class SpaceFullError(InvalidInputError):
    code = "espacio_lleno"


class NoAutenticadoError(DomainError):
    status_code = 401
    code = "no_autenticado"
    headers = {"WWW-Authenticate": "Bearer"}


class CredencialesInvalidasError(NoAutenticadoError):
    code = "credenciales_invalidas"


class DemasiadosIntentosError(DomainError):
    status_code = 429
    code = "demasiados_intentos"


class PdfError(DomainError):
    status_code = 500
    code = "pdf_error"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(
            {"detail": error.detail, "code": error.code},
            status_code=error.status_code,
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        errors = [{"loc": item["loc"], "msg": item["msg"]} for item in error.errors()]
        return JSONResponse(
            {"detail": "Datos inválidos", "code": "validation_error", "errors": errors},
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, error: Exception) -> JSONResponse:
        logger.exception("Error inesperado de la aplicación", exc_info=error)
        return JSONResponse({"detail": "Error interno", "code": "internal_error"}, status_code=500)
