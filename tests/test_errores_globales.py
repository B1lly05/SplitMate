import logging

import pytest
from fastapi.testclient import TestClient

from back.api.dependencias import get_servicio
from back.main import app

SECRETO = "detalle-interno-que-no-debe-salir"


@pytest.fixture
def cliente():
    # raise_server_exceptions=False: queremos ver la respuesta 500 que recibiría el navegador
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_un_error_no_controlado_devuelve_500_con_mensaje_claro_y_sin_detalles(cliente, caplog):
    def roto():
        raise RuntimeError(SECRETO)

    app.dependency_overrides[get_servicio] = roto
    caplog.set_level(logging.ERROR, logger="splitmate")
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com", "password": "clave-segura-1"})
    assert r.status_code == 500
    assert r.json() == {"error": "Ha ocurrido un error inesperado. Inténtalo de nuevo más tarde."}
    assert SECRETO not in r.text and "Traceback" not in r.text
    # el detalle técnico sí queda en el log del servidor
    assert SECRETO in caplog.text and "Traceback" in caplog.text


def test_una_ruta_inexistente_devuelve_404_con_el_formato_uniforme(cliente):
    r = cliente.get("/no-existe")
    assert r.status_code == 404 and set(r.json()) == {"error"}


def test_un_metodo_no_permitido_devuelve_405_con_el_formato_uniforme(cliente):
    r = cliente.post("/health")
    assert r.status_code == 405 and set(r.json()) == {"error"}


def test_datos_incompletos_devuelven_422_con_el_formato_uniforme(cliente):
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com"})
    assert r.status_code == 422
    assert r.json() == {"error": "Faltan datos o no son válidos."}


def test_un_cuerpo_que_no_es_json_devuelve_422_sin_detalles_internos(cliente):
    r = cliente.post("/auth/login", content="esto no es json",
                     headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and set(r.json()) == {"error"}


def test_los_errores_de_negocio_siguen_con_su_formato(cliente):
    r = cliente.post("/auth/login", json={"email": "nadie@ejemplo.com", "password": "clave-segura-1"})
    assert r.status_code == 401 and set(r.json()) == {"error"}
