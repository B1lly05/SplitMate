import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as HTTPExceptionStarlette

from back.logica.errores import (
    CredencialesInvalidas, CuentaNoDisponible, DatosInvalidos, EmailDuplicado, ErrorDeNegocio,
    GrupoNoEncontrado, NoAutenticado, NoAutorizado, TokenInvalido, UsuarioNoEncontrado,
    YaEsMiembro,
)

log = logging.getLogger("splitmate.api")

CODIGOS = {
    DatosInvalidos: 400, CredencialesInvalidas: 401, NoAutenticado: 401, NoAutorizado: 403,
    CuentaNoDisponible: 403, UsuarioNoEncontrado: 404, EmailDuplicado: 409,
    TokenInvalido: 400, GrupoNoEncontrado: 404, YaEsMiembro: 409,
}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeNegocio)
    async def manejar(request: Request, exc: ErrorDeNegocio):
        codigo = CODIGOS.get(type(exc), 400)
        # 401 y 403 son los intentos de acceso no permitidos: se registran como aviso
        nivel = logging.WARNING if codigo in (401, 403) else logging.INFO
        log.log(nivel, "%s %s -> %s: %s", request.method, request.url.path, codigo, exc)
        return JSONResponse(status_code=codigo, content={"error": str(exc)})

    # Todo error sale con el mismo formato, {"error": "<mensaje claro>"}, y nunca con
    # trazas ni detalles internos: el detalle técnico queda solo en el log del servidor.
    @app.exception_handler(RequestValidationError)
    async def manejar_validacion(request: Request, exc: RequestValidationError):
        log.info("%s %s -> 422: datos de entrada no válidos", request.method, request.url.path)
        return JSONResponse(status_code=422,
                            content={"error": "Faltan datos o no son válidos."})

    @app.exception_handler(HTTPExceptionStarlette)
    async def manejar_http(request: Request, exc: HTTPExceptionStarlette):
        mensajes = {404: "No se ha encontrado lo que buscas.",
                    405: "Esa operación no está permitida."}
        log.info("%s %s -> %s", request.method, request.url.path, exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": mensajes.get(exc.status_code, "No se pudo completar la petición.")},
        )

    @app.exception_handler(Exception)
    async def manejar_inesperado(request: Request, exc: Exception):
        # log.exception guarda la traza completa en el log; al cliente no se le cuenta nada
        log.exception("%s %s -> 500: error no controlado", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "Ha ocurrido un error inesperado. Inténtalo de nuevo más tarde."},
        )
