from datetime import datetime, timedelta, timezone

import pytest

from back.datos.memoria import RepositorioMemoria
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.logica.auth import ServicioAuth
from back.logica.errores import CredencialesInvalidas, CuentaNoDisponible, NoAutenticado
from back.logica.modelos import Estado
from back.logica.servicio import ServicioUsuarios

CLAVE = "clave-segura-1"


class Reloj:
    def __init__(self):
        self.ahora = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __call__(self):
        return self.ahora


@pytest.fixture
def reloj():
    return Reloj()


@pytest.fixture
def usuarios():
    return ServicioUsuarios(RepositorioMemoria())


@pytest.fixture
def auth(usuarios, reloj):
    return ServicioAuth(usuarios, RepositorioSesionesMemoria(), timedelta(hours=1), reloj)


def _activo(usuarios, email="ana@ejemplo.com"):
    u = usuarios.registrar(email, CLAVE)
    u.estado = Estado.ACTIVO
    usuarios.repositorio.actualizar(u)
    return u


def test_login_correcto_devuelve_token_y_usuario(auth, usuarios):
    ana = _activo(usuarios)
    token, usuario = auth.login("ana@ejemplo.com", CLAVE)
    assert token and usuario.id == ana.id


def test_login_con_contrasena_incorrecta_falla(auth, usuarios):
    _activo(usuarios)
    with pytest.raises(CredencialesInvalidas):
        auth.login("ana@ejemplo.com", "otra-clave-1")


def test_login_con_email_inexistente_falla_con_el_mismo_error(auth):
    with pytest.raises(CredencialesInvalidas):
        auth.login("nadie@ejemplo.com", CLAVE)


def test_login_con_cuenta_pendiente_falla(auth, usuarios):
    usuarios.registrar("ana@ejemplo.com", CLAVE)
    with pytest.raises(CuentaNoDisponible):
        auth.login("ana@ejemplo.com", CLAVE)


def test_login_con_cuenta_eliminada_falla(auth, usuarios):
    ana = _activo(usuarios)
    usuarios.eliminar(ana, ana.id)
    with pytest.raises(CuentaNoDisponible):
        auth.login("ana@ejemplo.com", CLAVE)


def test_la_sesion_identifica_al_usuario(auth, usuarios):
    ana = _activo(usuarios)
    token, _ = auth.login("ana@ejemplo.com", CLAVE)
    assert auth.usuario_de_sesion(token).id == ana.id


def test_logout_invalida_la_sesion_en_el_servidor(auth, usuarios):
    _activo(usuarios)
    token, _ = auth.login("ana@ejemplo.com", CLAVE)
    auth.logout(token)
    with pytest.raises(NoAutenticado):
        auth.usuario_de_sesion(token)


def test_sin_token_no_hay_sesion(auth):
    with pytest.raises(NoAutenticado):
        auth.usuario_de_sesion(None)


def test_token_inventado_no_vale(auth):
    with pytest.raises(NoAutenticado):
        auth.usuario_de_sesion("token-falso")


def test_la_sesion_caduca(auth, usuarios, reloj):
    _activo(usuarios)
    token, _ = auth.login("ana@ejemplo.com", CLAVE)
    reloj.ahora += timedelta(hours=2)
    with pytest.raises(NoAutenticado):
        auth.usuario_de_sesion(token)


def test_usuario_eliminado_pierde_la_sesion(auth, usuarios):
    ana = _activo(usuarios)
    token, _ = auth.login("ana@ejemplo.com", CLAVE)
    usuarios.eliminar(ana, ana.id)
    with pytest.raises(NoAutenticado):
        auth.usuario_de_sesion(token)