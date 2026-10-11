import os
from datetime import timedelta

from fastapi import Cookie, Depends

from back.datos.memoria import RepositorioMemoria
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.logica.auth import ServicioAuth
from back.logica.modelos import Usuario
from back.logica.servicio import ServicioUsuarios


def _activado(nombre: str) -> bool:
    return os.getenv(nombre, "false").strip().lower() in ("1", "true", "si", "sí")


# TEMPORAL hasta el Hito 4 (confirmación por correo)
CONFIRMAR_AUTOMATICAMENTE = _activado("CONFIRMAR_AUTOMATICAMENTE")
COOKIE_SEGURA = _activado("COOKIE_SEGURA")  # true en producción (https)
NOMBRE_COOKIE = "sesion"
DURACION_SESION = timedelta(hours=8)

# Aquí se montan las piezas. En el Hito 3 se cambiarán los repositorios en
# memoria por los de base de datos sin tocar la lógica.
_servicio = ServicioUsuarios(RepositorioMemoria(), CONFIRMAR_AUTOMATICAMENTE)
_auth = ServicioAuth(_servicio, RepositorioSesionesMemoria(), DURACION_SESION)


def get_servicio() -> ServicioUsuarios:
    return _servicio


def get_auth() -> ServicioAuth:
    return _auth


def usuario_de_sesion(
    sesion: str | None = Cookie(default=None),
    auth: ServicioAuth = Depends(get_auth),
) -> Usuario:
    return auth.usuario_de_sesion(sesion)