"""Confirmación de la cuenta por correo."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from back.api import dependencias as dep
from back.api.usuarios import UsuarioSalida
from back.logica.confirmacion import ServicioConfirmacion

router = APIRouter(prefix="/auth", tags=["auth"])

MENSAJE_REENVIO = (
    "Si existe una cuenta pendiente con ese correo, te hemos enviado un nuevo enlace."
)


class ConfirmarEntrada(BaseModel):
    token: str


class ReenviarEntrada(BaseModel):
    email: str


@router.post("/confirmar", response_model=UsuarioSalida)
def confirmar(datos: ConfirmarEntrada,
              confirmacion: ServicioConfirmacion = Depends(dep.get_confirmacion)):
    return confirmacion.confirmar(datos.token)


@router.post("/reenviar-confirmacion", status_code=202)
def reenviar(datos: ReenviarEntrada,
             confirmacion: ServicioConfirmacion = Depends(dep.get_confirmacion)):
    confirmacion.reenviar(datos.email)
    # Misma respuesta exista o no la cuenta: no se revela qué correos están registrados
    return JSONResponse(status_code=202, content={"mensaje": MENSAJE_REENVIO})
