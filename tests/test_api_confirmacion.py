from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from back.api.dependencias import get_auth, get_confirmacion, get_servicio
from back.datos.memoria import RepositorioMemoria
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.datos.tokens_memoria import RepositorioTokensMemoria
from back.externos.correo_simulado import EnviadorSimulado
from back.logica.auth import ServicioAuth
from back.logica.confirmacion import ServicioConfirmacion
from back.logica.servicio import ServicioUsuarios
from back.main import app

CLAVE = "clave-segura-1"


@pytest.fixture
def entorno():
    usuarios = ServicioUsuarios(RepositorioMemoria())  # sin confirmación automática
    enviador = EnviadorSimulado()
    confirmacion = ServicioConfirmacion(
        usuarios, RepositorioTokensMemoria(), enviador, "http://127.0.0.1:8000",
        espera_reenvio=timedelta(0),
    )
    auth = ServicioAuth(usuarios, RepositorioSesionesMemoria())
    app.dependency_overrides[get_servicio] = lambda: usuarios
    app.dependency_overrides[get_auth] = lambda: auth
    app.dependency_overrides[get_confirmacion] = lambda: confirmacion
    yield TestClient(app), enviador
    app.dependency_overrides.clear()


def _registrar(cliente, email="ana@ejemplo.com"):
    return cliente.post("/usuarios", json={"email": email, "password": CLAVE})


def _token(enviador):
    return enviador.enviados[-1][1].split("?confirmar=")[1]


def _login(cliente, email="ana@ejemplo.com"):
    return cliente.post("/auth/login", json={"email": email, "password": CLAVE})


def test_el_registro_envia_el_correo_de_confirmacion(entorno):
    cliente, enviador = entorno
    r = _registrar(cliente)
    assert r.status_code == 201 and r.json()["estado"] == "pendiente"
    assert [d for d, _ in enviador.enviados] == ["ana@ejemplo.com"]


def test_un_registro_invalido_no_envia_correo(entorno):
    cliente, enviador = entorno
    assert _registrar(cliente, "no-es-email").status_code == 400
    assert enviador.enviados == []


def test_si_falla_el_envio_el_registro_sigue_siendo_correcto(entorno):
    cliente, enviador = entorno
    enviador.fallar = True
    assert _registrar(cliente).status_code == 201


def test_sin_confirmar_no_se_puede_iniciar_sesion(entorno):
    cliente, _ = entorno
    _registrar(cliente)
    assert _login(cliente).status_code == 403


def test_confirmar_con_el_enlace_permite_iniciar_sesion(entorno):
    cliente, enviador = entorno
    _registrar(cliente)
    r = cliente.post("/auth/confirmar", json={"token": _token(enviador)})
    assert r.status_code == 200 and r.json()["estado"] == "activo"
    assert _login(cliente).status_code == 200


def test_el_enlace_no_se_puede_usar_dos_veces(entorno):
    cliente, enviador = entorno
    _registrar(cliente)
    token = _token(enviador)
    cliente.post("/auth/confirmar", json={"token": token})
    assert cliente.post("/auth/confirmar", json={"token": token}).status_code == 400


def test_un_token_inventado_devuelve_400_con_mensaje_claro(entorno):
    cliente, _ = entorno
    r = cliente.post("/auth/confirmar", json={"token": "inventado"})
    assert r.status_code == 400 and "caducado" in r.json()["error"]


def test_confirmar_sin_token_devuelve_422(entorno):
    cliente, _ = entorno
    assert cliente.post("/auth/confirmar", json={}).status_code == 422


def test_reenviar_responde_lo_mismo_exista_o_no_la_cuenta(entorno):
    cliente, enviador = entorno
    _registrar(cliente)
    existe = cliente.post("/auth/reenviar-confirmacion", json={"email": "ana@ejemplo.com"})
    no_existe = cliente.post("/auth/reenviar-confirmacion", json={"email": "nadie@ejemplo.com"})
    assert existe.status_code == no_existe.status_code == 202
    assert existe.json() == no_existe.json()
    assert len(enviador.enviados) == 2  # el del registro y el del reenvío a ana


def test_el_enlace_reenviado_funciona_y_el_viejo_deja_de_valer(entorno):
    cliente, enviador = entorno
    _registrar(cliente)
    viejo = _token(enviador)
    cliente.post("/auth/reenviar-confirmacion", json={"email": "ana@ejemplo.com"})
    nuevo = _token(enviador)
    assert cliente.post("/auth/confirmar", json={"token": viejo}).status_code == 400
    assert cliente.post("/auth/confirmar", json={"token": nuevo}).status_code == 200
