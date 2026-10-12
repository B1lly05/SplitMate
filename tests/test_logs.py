import logging

import pytest
from fastapi.testclient import TestClient

from back.api.dependencias import get_auth, get_servicio
from back.datos.memoria import RepositorioMemoria
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.logica.auth import ServicioAuth
from back.logica.errores import CredencialesInvalidas, NoAutorizado
from back.logica.modelos import Estado, Rol
from back.logica.servicio import ServicioUsuarios
from back.main import app

CLAVE = "clave-muy-secreta-1"


@pytest.fixture(autouse=True)
def captura(caplog):
    caplog.set_level(logging.DEBUG, logger="splitmate")


@pytest.fixture
def usuarios():
    return ServicioUsuarios(RepositorioMemoria())


@pytest.fixture
def auth(usuarios):
    return ServicioAuth(usuarios, RepositorioSesionesMemoria())


def _activo(usuarios, email="ana@ejemplo.com", rol=Rol.USUARIO):
    u = usuarios.registrar(email, CLAVE, rol)
    u.estado = Estado.ACTIVO
    usuarios.repositorio.actualizar(u)
    return u


def test_se_registra_el_alta_de_usuarios(usuarios, caplog):
    usuarios.registrar("ana@ejemplo.com", CLAVE)
    assert "Usuario registrado id=1" in caplog.text


def test_se_registra_el_inicio_de_sesion_correcto(usuarios, auth, caplog):
    _activo(usuarios)
    auth.login("ana@ejemplo.com", CLAVE)
    assert "Inicio de sesión correcto id=1" in caplog.text


def test_se_registra_el_inicio_de_sesion_fallido(usuarios, auth, caplog):
    _activo(usuarios)
    with pytest.raises(CredencialesInvalidas):
        auth.login("ana@ejemplo.com", "mala-clave-99")
    registro = next(r for r in caplog.records if "fallido" in r.getMessage())
    assert registro.levelno == logging.WARNING
    assert "ana@ejemplo.com" in registro.getMessage()


def test_se_registra_el_cierre_de_sesion(usuarios, auth, caplog):
    _activo(usuarios)
    token, _ = auth.login("ana@ejemplo.com", CLAVE)
    auth.logout(token)
    assert "Sesión cerrada" in caplog.text


def test_se_registra_la_eliminacion_de_usuarios(usuarios, caplog):
    admin = _activo(usuarios, "admin@ejemplo.com", Rol.ADMIN)
    ana = _activo(usuarios)
    usuarios.eliminar(admin, ana.id)
    assert f"Usuario eliminado id={ana.id} por id={admin.id}" in caplog.text


def test_se_registra_el_intento_de_eliminar_una_cuenta_ajena(usuarios, caplog):
    ana = _activo(usuarios)
    luis = _activo(usuarios, "luis@ejemplo.com")
    with pytest.raises(NoAutorizado):
        usuarios.eliminar(ana, luis.id)
    assert any(r.levelno == logging.WARNING and "cuenta ajena" in r.getMessage()
               for r in caplog.records)


def test_se_registra_el_acceso_denegado_a_funciones_de_administrador(usuarios, caplog):
    ana = _activo(usuarios)
    with pytest.raises(NoAutorizado):
        usuarios.listar(ana)
    assert any(r.levelno == logging.WARNING and "Acceso denegado" in r.getMessage()
               for r in caplog.records)


def test_los_logs_no_contienen_contrasenas_tokens_ni_hashes(usuarios, auth, caplog):
    ana = _activo(usuarios)
    token, _ = auth.login("ana@ejemplo.com", CLAVE)
    with pytest.raises(CredencialesInvalidas):
        auth.login("ana@ejemplo.com", "otra-clave-secreta-2")
    auth.logout(token)
    usuarios.eliminar(ana, ana.id)
    texto = caplog.text
    assert CLAVE not in texto
    assert "otra-clave-secreta-2" not in texto
    assert token not in texto
    assert "$argon2" not in texto


def test_la_api_registra_los_accesos_no_autorizados(usuarios, auth, caplog):
    app.dependency_overrides[get_servicio] = lambda: usuarios
    app.dependency_overrides[get_auth] = lambda: auth
    try:
        assert TestClient(app).get("/usuarios").status_code == 401
    finally:
        app.dependency_overrides.clear()
    assert any(r.levelno == logging.WARNING and "GET /usuarios -> 401" in r.getMessage()
               for r in caplog.records)