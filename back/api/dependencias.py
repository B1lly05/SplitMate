import logging
from datetime import timedelta
from functools import lru_cache

from fastapi import Cookie, Depends

from back import config
from back.datos.memoria import RepositorioMemoria
from back.datos.mongo import crear_repositorios_mongo
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.logica.auth import ServicioAuth
from back.logica.modelos import Usuario
from back.logica.servicio import ServicioUsuarios
from back.logica.errores import ErrorDeNegocio

log = logging.getLogger("splitmate")

COOKIE_SEGURA = config.COOKIE_SEGURA
NOMBRE_COOKIE = "sesion"
DURACION_SESION = timedelta(hours=8)


@lru_cache
def _componentes():
    """Ensambla las piezas. Es el único sitio que decide qué repositorios se usan:
    cambiar de memoria a base de datos no toca la capa de lógica."""
    if config.MONGODB_URI:
        usuarios, sesiones = crear_repositorios_mongo(
            config.MONGODB_URI, config.MONGODB_DB
        )
        log.info("Usando MongoDB (base de datos '%s')", config.MONGODB_DB)
    else:
        usuarios, sesiones = RepositorioMemoria(), RepositorioSesionesMemoria()
        log.warning(
            "MONGODB_URI no definida: usando memoria (los datos no se conservan)"
        )
    servicio = ServicioUsuarios(usuarios, config.CONFIRMAR_AUTOMATICAMENTE)
    return servicio, ServicioAuth(servicio, sesiones, DURACION_SESION)


def preparar() -> None:
    """Se llama al arrancar: si la base de datos falla, la aplicación no arranca."""
    servicio, _ = _componentes()
    if config.ADMIN_EMAIL and config.ADMIN_PASSWORD:
        try:
            if servicio.crear_admin_inicial(config.ADMIN_EMAIL, config.ADMIN_PASSWORD):
                log.info("Administrador inicial creado")
            else:
                log.info("El administrador inicial ya existe: no se modifica")
        except ErrorDeNegocio as error:
            log.warning("No se pudo crear el administrador inicial: %s", error)


def get_servicio() -> ServicioUsuarios:
    return _componentes()[0]


def get_auth() -> ServicioAuth:
    return _componentes()[1]


def usuario_de_sesion(
    sesion: str | None = Cookie(default=None),
    auth: ServicioAuth = Depends(get_auth),
) -> Usuario:
    return auth.usuario_de_sesion(sesion)
