import logging
from datetime import timedelta
from functools import lru_cache

from fastapi import Cookie, Depends, Response

from back import config
from back.datos.memoria import RepositorioMemoria
from back.datos.mongo import crear_repositorios_mongo
from back.datos.grupos_memoria import RepositorioGruposMemoria
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.datos.tokens_memoria import RepositorioTokensMemoria
from back.externos.brevo import EnviadorBrevo
from back.externos.correo_simulado import EnviadorSimulado
from back.externos.github import ProveedorGitHub
from back.logica.confirmacion import ServicioConfirmacion
from back.logica.correo import EnviadorCorreo
from back.logica.grupos import ServicioGrupos
from back.logica.auth import ServicioAuth
from back.logica.modelos import Usuario
from back.logica.servicio import ServicioUsuarios
from back.logica.errores import ErrorDeNegocio

log = logging.getLogger("splitmate")

COOKIE_SEGURA = config.COOKIE_SEGURA
NOMBRE_COOKIE = "sesion"
DURACION_SESION = timedelta(hours=8)


def _crear_enviador() -> EnviadorCorreo:
    if config.BREVO_API_KEY and config.MAIL_REMITENTE:
        log.info("Correo: usando Brevo")
        return EnviadorBrevo(config.BREVO_API_KEY, config.MAIL_REMITENTE, config.MAIL_NOMBRE)
    log.warning("Brevo no configurado: los correos de confirmación no se enviarán")
    return EnviadorSimulado(avisar=True)


@lru_cache
def _componentes():
    """Ensambla las piezas. Es el único sitio que decide qué repositorios se usan:
    cambiar de memoria a base de datos no toca la capa de lógica."""
    if config.MONGODB_URI:
        usuarios, sesiones, tokens, grupos = crear_repositorios_mongo(
            config.MONGODB_URI, config.MONGODB_DB
        )
        log.info("Usando MongoDB (base de datos '%s')", config.MONGODB_DB)
    else:
        usuarios, sesiones = RepositorioMemoria(), RepositorioSesionesMemoria()
        tokens, grupos = RepositorioTokensMemoria(), RepositorioGruposMemoria()
        log.warning(
            "MONGODB_URI no definida: usando memoria (los datos no se conservan)"
        )
    servicio = ServicioUsuarios(usuarios, config.CONFIRMAR_AUTOMATICAMENTE)
    confirmacion = ServicioConfirmacion(servicio, tokens, _crear_enviador(), config.BASE_URL)
    servicio_grupos = ServicioGrupos(grupos, servicio)
    return (servicio, ServicioAuth(servicio, sesiones, DURACION_SESION), confirmacion,
            servicio_grupos)


def preparar() -> None:
    """Se llama al arrancar: si la base de datos falla, la aplicación no arranca."""
    servicio = _componentes()[0]
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


def get_confirmacion() -> ServicioConfirmacion:
    return _componentes()[2]


def get_grupos() -> ServicioGrupos:
    return _componentes()[3]


def usuario_de_sesion(
    sesion: str | None = Cookie(default=None),
    auth: ServicioAuth = Depends(get_auth),
) -> Usuario:
    return auth.usuario_de_sesion(sesion)


def get_proveedor() -> ProveedorGitHub:
    """Proveedor OAuth. Se ensambla aquí para poder sustituirlo en las pruebas."""
    return ProveedorGitHub(config.GITHUB_CLIENT_ID, config.GITHUB_CLIENT_SECRET)


def poner_cookie_sesion(response: Response, token: str) -> None:
    """Cookie de sesión: HttpOnly, SameSite=Lax y Secure en producción."""
    response.set_cookie(
        NOMBRE_COOKIE, token,
        httponly=True, samesite="lax", secure=COOKIE_SEGURA,
        max_age=int(DURACION_SESION.total_seconds()), path="/",
    )
