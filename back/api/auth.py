from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel

from back.api import dependencias as dep
from back.api.usuarios import UsuarioSalida
from back.logica.auth import ServicioAuth
from back.logica.modelos import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginEntrada(BaseModel):
    email: str
    password: str


@router.post("/login", response_model=UsuarioSalida)
def login(datos: LoginEntrada, response: Response,
          auth: ServicioAuth = Depends(dep.get_auth)):
    token, usuario = auth.login(datos.email, datos.password)
    response.set_cookie(
        dep.NOMBRE_COOKIE, token,
        httponly=True, samesite="lax", secure=dep.COOKIE_SEGURA,
        max_age=int(dep.DURACION_SESION.total_seconds()), path="/",
    )
    return usuario


@router.post("/logout", status_code=204)
def logout(sesion: str | None = Cookie(default=None),
           auth: ServicioAuth = Depends(dep.get_auth)):
    if sesion:
        auth.logout(sesion)  # la sesión se invalida en el servidor
    respuesta = Response(status_code=204)
    respuesta.delete_cookie(dep.NOMBRE_COOKIE, path="/")
    return respuesta


@router.get("/sesion", response_model=UsuarioSalida)
def sesion_actual(usuario: Usuario = Depends(dep.usuario_de_sesion)):
    return usuario