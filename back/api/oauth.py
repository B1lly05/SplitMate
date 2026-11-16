"""Inicio de sesión con GitHub (OAuth 2.0, flujo de código de autorización)."""
import logging
import secrets

from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import RedirectResponse

from back import config
from back.api import dependencias as dep
from back.externos.github import ErrorProveedor, ProveedorGitHub, SinEmailVerificado
from back.logica.auth import ServicioAuth
from back.logica.errores import CuentaNoDisponible, DatosInvalidos

log = logging.getLogger("splitmate.oauth")

router = APIRouter(prefix="/auth/github", tags=["auth"])

COOKIE_STATE = "oauth_state"
RUTA_CALLBACK = "/auth/github/callback"


def _redirect_uri() -> str:
    return config.BASE_URL + RUTA_CALLBACK


def _error(codigo: str) -> RedirectResponse:
    """Los fallos vuelven a la portada con un código fijo (nunca texto de GitHub)."""
    respuesta = RedirectResponse(f"/?error={codigo}", status_code=303)
    respuesta.delete_cookie(COOKIE_STATE, path="/auth/github")  # el state vale una sola vez
    return respuesta


@router.get("/login")
def login(proveedor: ProveedorGitHub = Depends(dep.get_proveedor)):
    if not proveedor.configurado():
        log.warning("OAuth con GitHub no configurado")
        return RedirectResponse("/?error=oauth_no_configurado", status_code=303)
    # state aleatorio contra CSRF: se guarda en una cookie y GitHub nos lo devuelve
    state = secrets.token_urlsafe(32)
    respuesta = RedirectResponse(
        proveedor.url_autorizacion(state, _redirect_uri()), status_code=303
    )
    respuesta.set_cookie(
        COOKIE_STATE, state,
        httponly=True, samesite="lax", secure=dep.COOKIE_SEGURA,
        max_age=600, path="/auth/github",
    )
    return respuesta


@router.get("/callback")
def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None),
    proveedor: ProveedorGitHub = Depends(dep.get_proveedor),
    auth: ServicioAuth = Depends(dep.get_auth),
):
    if error:
        log.info("El usuario canceló el acceso con GitHub")
        return _error("oauth_cancelado")
    if (not code or not state or not oauth_state
            or not secrets.compare_digest(state, oauth_state)):
        log.warning("Callback de GitHub con state no válido")
        return _error("oauth_fallo")
    try:
        email = proveedor.obtener_email_verificado(code, _redirect_uri())
        token, _ = auth.login_externo(email)
    except SinEmailVerificado:
        return _error("oauth_sin_email")
    except ErrorProveedor:
        log.warning("Fallo al hablar con GitHub")
        return _error("oauth_fallo")
    except DatosInvalidos:
        return _error("oauth_sin_email")
    except CuentaNoDisponible:
        return _error("cuenta_eliminada")
    respuesta = RedirectResponse("/", status_code=303)
    dep.poner_cookie_sesion(respuesta, token)
    respuesta.delete_cookie(COOKIE_STATE, path="/auth/github")
    return respuesta
