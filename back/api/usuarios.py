from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from back.api.dependencias import get_servicio, solicitante_actual
from back.logica.modelos import Estado, Rol, Usuario
from back.logica.servicio import ServicioUsuarios

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class RegistroEntrada(BaseModel):
    email: str
    password: str


class UsuarioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    rol: Rol
    estado: Estado


@router.post("", response_model=UsuarioSalida, status_code=201)
def registro(datos: RegistroEntrada, servicio: ServicioUsuarios = Depends(get_servicio)):
    # El rol nunca se acepta desde fuera: todo registro es un usuario normal
    return servicio.registrar(datos.email, datos.password)

@router.get("", response_model=list[UsuarioSalida])
def listar(
    solicitante: Usuario = Depends(solicitante_actual),
    servicio: ServicioUsuarios = Depends(get_servicio),
):
    return servicio.listar(solicitante)


@router.get("/{id_usuario}/activo")
def esta_activo(
    id_usuario: int,
    solicitante: Usuario = Depends(solicitante_actual),
    servicio: ServicioUsuarios = Depends(get_servicio),
):
    return {"activo": servicio.esta_activo(solicitante, id_usuario)}


@router.delete("/{id_usuario}", status_code=204)
def eliminar(
    id_usuario: int,
    solicitante: Usuario = Depends(solicitante_actual),
    servicio: ServicioUsuarios = Depends(get_servicio),
):
    servicio.eliminar(solicitante, id_usuario)
    return Response(status_code=204)