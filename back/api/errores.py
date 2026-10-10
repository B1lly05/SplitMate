from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from back.logica.errores import (
    CuentaNoDisponible,
    DatosInvalidos,
    EmailDuplicado,
    ErrorDeNegocio,
    NoAutenticado,
    NoAutorizado,
    UsuarioNoEncontrado,
    CredencialesInvalidas
)

CODIGOS = {
    DatosInvalidos: 400,
    NoAutenticado: 401,
    NoAutorizado: 403,
    CuentaNoDisponible: 403,
    UsuarioNoEncontrado: 404,
    EmailDuplicado: 409,
    CredencialesInvalidas: 401,
}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeNegocio)
    async def manejar(request: Request, exc: ErrorDeNegocio):
        return JSONResponse(status_code=CODIGOS.get(type(exc), 400), content={"error": str(exc)})