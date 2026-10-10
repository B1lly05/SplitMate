import pytest
from fastapi.testclient import TestClient

from back.api.dependencias import get_servicio
from back.datos.memoria import RepositorioMemoria
from back.logica.modelos import Rol
from back.logica.servicio import ServicioUsuarios
from back.main import app


@pytest.fixture
def servicio():
    return ServicioUsuarios(RepositorioMemoria())


@pytest.fixture
def cliente(servicio):
    app.dependency_overrides[get_servicio] = lambda: servicio
    yield TestClient(app)
    app.dependency_overrides.clear()


def _cabecera(usuario):
    return {"X-Usuario-Id": str(usuario.id)}


def test_alta_devuelve_201_y_usuario_pendiente(cliente):
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com"})
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente"


def test_alta_ignora_el_rol_enviado(cliente):
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com", "rol": "admin"})
    assert r.json()["rol"] == "usuario"


def test_alta_duplicada_devuelve_409(cliente):
    cliente.post("/usuarios", json={"email": "ana@ejemplo.com"})
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com"})
    assert r.status_code == 409


def test_alta_con_email_invalido_devuelve_400(cliente):
    r = cliente.post("/usuarios", json={"email": "no-es-email"})
    assert r.status_code == 400


def test_listar_sin_identificarse_devuelve_401(cliente):
    assert cliente.get("/usuarios").status_code == 401


def test_listar_como_usuario_normal_devuelve_403(cliente, servicio):
    normal = servicio.alta("ana@ejemplo.com")
    assert cliente.get("/usuarios", headers=_cabecera(normal)).status_code == 403


def test_listar_como_admin_devuelve_200(cliente, servicio):
    admin = servicio.alta("admin@ejemplo.com", Rol.ADMIN)
    servicio.alta("ana@ejemplo.com")
    r = cliente.get("/usuarios", headers=_cabecera(admin))
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_consultar_activo_como_admin(cliente, servicio):
    admin = servicio.alta("admin@ejemplo.com", Rol.ADMIN)
    ana = servicio.alta("ana@ejemplo.com")
    r = cliente.get(f"/usuarios/{ana.id}/activo", headers=_cabecera(admin))
    assert r.status_code == 200
    assert r.json() == {"activo": False}


def test_usuario_normal_no_puede_eliminar_a_otro(cliente, servicio):
    ana = servicio.alta("ana@ejemplo.com")
    luis = servicio.alta("luis@ejemplo.com")
    r = cliente.delete(f"/usuarios/{luis.id}", headers=_cabecera(ana))
    assert r.status_code == 403


def test_usuario_puede_eliminar_su_propia_cuenta(cliente, servicio):
    ana = servicio.alta("ana@ejemplo.com")
    r = cliente.delete(f"/usuarios/{ana.id}", headers=_cabecera(ana))
    assert r.status_code == 204