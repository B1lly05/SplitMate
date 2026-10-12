import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from back.logica.errores import (
    CredencialesInvalidas, CuentaNoDisponible, DatosInvalidos, EmailDuplicado, ErrorDeNegocio,
    NoAutenticado, NoAutorizado, UsuarioNoEncontrado,
)

log = logging.getLogger("splitmate.api")

CODIGOS = {
    DatosInvalidos: 400, CredencialesInvalidas: 401, NoAutenticado: 401, NoAutorizado: 403,
    CuentaNoDisponible: 403, UsuarioNoEncontrado: 404, EmailDuplicado: 409,
}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeNegocio)
    async def manejar(request: Request, exc: ErrorDeNegocio):
        codigo = CODIGOS.get(type(exc), 400)
        # 401 y 403 son los intentos de acceso no permitidos: se registran como aviso
        nivel = logging.WARNING if codigo in (401, 403) else logging.INFO
        log.log(nivel, "%s %s -> %s: %s", request.method, request.url.path, codigo, exc)
        return JSONResponse(status_code=codigo, content={"error": str(exc)})