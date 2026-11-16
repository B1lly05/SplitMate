from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from back.api.dependencias import get_auth, get_proveedor, get_servicio
from back.datos.memoria import RepositorioMemoria
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.externos.github import ErrorProveedor, SinEmailVerificado
from back.logica.auth import ServicioAuth
from back.logica.modelos import Estado
from back.logica.servicio import ServicioUsuarios
from back.main import app


class ProveedorFalso:
    def __init__(self, resultado="ana@ejemplo.com", configurado=True):
        self.resultado = resultado
        self._configurado = configurado

    def configurado(self):
        return self._configurado

    def url_autorizacion(self, state, redirect_uri):
        return f"https://github.com/login/oauth/authorize?state={state}&redirect_uri={redirect_uri}"

    def obtener_email_verificado(self, code, redirect_uri):
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


@pytest.fixture
def entorno():
    usuarios = ServicioUsuarios(RepositorioMemoria())
    auth = ServicioAuth(usuarios, RepositorioSesionesMemoria())
    proveedor = ProveedorFalso()
    app.dependency_overrides[get_servicio] = lambda: usuarios
    app.dependency_overrides[get_auth] = lambda: auth
    app.dependency_overrides[get_proveedor] = lambda: proveedor
    cliente = TestClient(app, follow_redirects=False)
    yield cliente, usuarios, proveedor
    app.dependency_overrides.clear()


def _iniciar_flujo(cliente):
    r = cliente.get("/auth/github/login")
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    return r, state


def test_login_redirige_a_github_con_state_y_cookie(entorno):
    cliente, _, _ = entorno
    r, state = _iniciar_flujo(cliente)
    assert r.status_code == 303
    assert r.headers["location"].startswith("https://github.com/")
    assert cliente.cookies.get("oauth_state") == state
    assert "httponly" in r.headers["set-cookie"].lower()


def test_cada_inicio_genera_un_state_distinto(entorno):
    cliente, _, _ = entorno
    assert _iniciar_flujo(cliente)[1] != _iniciar_flujo(cliente)[1]


def test_sin_configurar_vuelve_con_error(entorno):
    cliente, _, proveedor = entorno
    proveedor._configurado = False
    r = cliente.get("/auth/github/login")
    assert r.headers["location"] == "/?error=oauth_no_configurado"


def test_callback_correcto_crea_la_sesion_y_entra(entorno):
    cliente, usuarios, _ = entorno
    _, state = _iniciar_flujo(cliente)
    r = cliente.get("/auth/github/callback", params={"code": "c", "state": state})
    assert r.status_code == 303 and r.headers["location"] == "/"
    sesion = cliente.get("/auth/sesion")
    assert sesion.status_code == 200 and sesion.json()["email"] == "ana@ejemplo.com"
    assert usuarios.repositorio.obtener_por_email("ana@ejemplo.com").estado == Estado.ACTIVO


def test_callback_con_state_distinto_se_rechaza(entorno):
    cliente, _, _ = entorno
    _iniciar_flujo(cliente)
    r = cliente.get("/auth/github/callback", params={"code": "c", "state": "otro"})
    assert r.headers["location"] == "/?error=oauth_fallo"
    assert cliente.get("/auth/sesion").status_code == 401


def test_callback_sin_flujo_previo_se_rechaza(entorno):
    cliente, _, _ = entorno
    r = cliente.get("/auth/github/callback", params={"code": "c", "state": "x"})
    assert r.headers["location"] == "/?error=oauth_fallo"


def test_callback_sin_codigo_se_rechaza(entorno):
    cliente, _, _ = entorno
    _, state = _iniciar_flujo(cliente)
    r = cliente.get("/auth/github/callback", params={"state": state})
    assert r.headers["location"] == "/?error=oauth_fallo"


def test_callback_cancelado_por_el_usuario(entorno):
    cliente, _, _ = entorno
    r = cliente.get("/auth/github/callback", params={"error": "access_denied"})
    assert r.headers["location"] == "/?error=oauth_cancelado"


@pytest.mark.parametrize("fallo,codigo", [
    (SinEmailVerificado("x"), "oauth_sin_email"),
    (ErrorProveedor("x"), "oauth_fallo"),
])
def test_fallos_del_proveedor_vuelven_con_codigo_fijo(entorno, fallo, codigo):
    cliente, _, proveedor = entorno
    proveedor.resultado = fallo
    _, state = _iniciar_flujo(cliente)
    r = cliente.get("/auth/github/callback", params={"code": "c", "state": state})
    assert r.headers["location"] == f"/?error={codigo}"
    assert cliente.get("/auth/sesion").status_code == 401


def test_cuenta_eliminada_no_entra_por_oauth(entorno):
    cliente, usuarios, _ = entorno
    u = usuarios.acceso_externo("ana@ejemplo.com")
    u.estado = Estado.ELIMINADO
    usuarios.repositorio.actualizar(u)
    _, state = _iniciar_flujo(cliente)
    r = cliente.get("/auth/github/callback", params={"code": "c", "state": state})
    assert r.headers["location"] == "/?error=cuenta_eliminada"
    assert cliente.get("/auth/sesion").status_code == 401


def test_el_state_solo_vale_una_vez(entorno):
    cliente, _, _ = entorno
    _, state = _iniciar_flujo(cliente)
    cliente.get("/auth/github/callback", params={"code": "c", "state": state})
    cliente.cookies.delete("sesion")
    r = cliente.get("/auth/github/callback", params={"code": "c", "state": state})
    assert r.headers["location"] == "/?error=oauth_fallo"
