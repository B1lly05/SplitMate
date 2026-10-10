import pytest
from fastapi.testclient import TestClient

from back.api.dependencias import get_auth, get_servicio
from back.datos.memoria import RepositorioMemoria
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.logica.auth import ServicioAuth
from back.logica.modelos import Estado
from back.logica.servicio import ServicioUsuarios
from back.main import app

CLAVE = "clave-segura-1"


@pytest.fixture
def usuarios():
    return ServicioUsuarios(RepositorioMemoria())


@pytest.fixture
def cliente(usuarios):
    auth = ServicioAuth(usuarios, RepositorioSesionesMemoria())
    app.dependency_overrides[get_servicio] = lambda: usuarios
    app.dependency_overrides[get_auth] = lambda: auth
    yield TestClient(app)
    app.dependency_overrides.clear()


def _crear_activo(usuarios):
    u = usuarios.registrar("ana@ejemplo.com", CLAVE)
    u.estado = Estado.ACTIVO
    usuarios.repositorio.actualizar(u)


def _login(cliente, password=CLAVE):
    return cliente.post("/auth/login", json={"email": "ana@ejemplo.com", "password": password})


def test_login_correcto_devuelve_200_y_cookie_httponly(cliente, usuarios):
    _crear_activo(usuarios)
    r = _login(cliente)
    assert r.status_code == 200
    assert "httponly" in r.headers["set-cookie"].lower()
    assert "password" not in r.json()


def test_login_con_contrasena_incorrecta_devuelve_401(cliente, usuarios):
    _crear_activo(usuarios)
    assert _login(cliente, "incorrecta-1").status_code == 401


def test_login_con_cuenta_pendiente_devuelve_403(cliente, usuarios):
    usuarios.registrar("ana@ejemplo.com", CLAVE)
    assert _login(cliente).status_code == 403


def test_sesion_sin_login_devuelve_401(cliente):
    assert cliente.get("/auth/sesion").status_code == 401


def test_sesion_tras_login_devuelve_el_usuario(cliente, usuarios):
    _crear_activo(usuarios)
    _login(cliente)
    r = cliente.get("/auth/sesion")
    assert r.status_code == 200 and r.json()["email"] == "ana@ejemplo.com"


def test_logout_cierra_la_sesion(cliente, usuarios):
    _crear_activo(usuarios)
    _login(cliente)
    assert cliente.post("/auth/logout").status_code == 204
    assert cliente.get("/auth/sesion").status_code == 401


def test_un_token_robado_no_vale_tras_el_logout(cliente, usuarios):
    _crear_activo(usuarios)
    _login(cliente)
    token = cliente.cookies.get("sesion")
    cliente.post("/auth/logout")
    cliente.cookies.set("sesion", token)  # el atacante reutiliza el token
    assert cliente.get("/auth/sesion").status_code == 401