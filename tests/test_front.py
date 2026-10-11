from fastapi.testclient import TestClient

from back.main import app

cliente = TestClient(app)


def test_la_raiz_sirve_la_interfaz():
    r = cliente.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "SplitMate" in r.text


def test_se_sirven_los_archivos_del_frontend():
    for ruta in [
        "/front/gui/estilos.css",
        "/front/gui/vista.js",
        "/front/controlador/controlador.js",
        "/front/com/clienteApi.js",
    ]:
        assert cliente.get(ruta).status_code == 200, ruta


def test_la_interfaz_y_la_api_comparten_origen():
    # Mismo servidor: la web y la API responden en el mismo host
    assert cliente.get("/").status_code == 200
    assert cliente.get("/health").status_code == 200