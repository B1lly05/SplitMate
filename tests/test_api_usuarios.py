import pytest
from fastapi.testclient import TestClient

from back.api.dependencias import get_auth, get_servicio
from back.datos.memoria import RepositorioMemoria
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.logica.auth import ServicioAuth
from back.logica.modelos import Estado, Rol
from back.logica.servicio import ServicioUsuarios
from back.main import app

CLAVE = "clave-segura-1"


@pytest.fixture
def servicio():
    return ServicioUsuarios(RepositorioMemoria())


@pytest.fixture
def cliente(servicio):
    auth = ServicioAuth(servicio, RepositorioSesionesMemoria())
    app.dependency_overrides[get_servicio] = lambda: servicio
    app.dependency_overrides[get_auth] = lambda: auth
    yield TestClient(app)
    app.dependency_overrides.clear()


def _crear(servicio, email, rol=Rol.USUARIO):
    usuario = servicio.registrar(email, CLAVE, rol)
    usuario.estado = Estado.ACTIVO
    servicio.repositorio.actualizar(usuario)
    return usuario


def _entrar(cliente, email):
    r = cliente.post("/auth/login", json={"email": email, "password": CLAVE})
    assert r.status_code == 200


# ---- Registro (ruta pública) ----
def test_registro_devuelve_201_y_usuario_pendiente(cliente):
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com", "password": CLAVE})
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente"


def test_registro_no_devuelve_la_contrasena_ni_el_hash(cliente):
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com", "password": CLAVE})
    assert "password" not in r.json()
    assert "password_hash" not in r.json()


def test_registro_ignora_el_rol_enviado(cliente):
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com", "password": CLAVE, "rol": "admin"})
    assert r.json()["rol"] == "usuario"


def test_registro_duplicado_devuelve_409(cliente):
    cliente.post("/usuarios", json={"email": "ana@ejemplo.com", "password": CLAVE})
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com", "password": CLAVE})
    assert r.status_code == 409


def test_registro_con_email_invalido_devuelve_400(cliente):
    r = cliente.post("/usuarios", json={"email": "no-es-email", "password": CLAVE})
    assert r.status_code == 400


def test_registro_con_contrasena_corta_devuelve_400(cliente):
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com", "password": "corta"})
    assert r.status_code == 400


def test_registro_sin_contrasena_devuelve_422(cliente):
    r = cliente.post("/usuarios", json={"email": "ana@ejemplo.com"})
    assert r.status_code == 422


# ---- Rutas protegidas: sin sesión válida se rechazan ----
@pytest.mark.parametrize("metodo,ruta", [
    ("get", "/usuarios"),
    ("get", "/usuarios/1/activo"),
    ("delete", "/usuarios/1"),
    ("get", "/auth/sesion"),
])
def test_rutas_privadas_rechazan_peticiones_sin_sesion(cliente, metodo, ruta):
    assert getattr(cliente, metodo)(ruta).status_code == 401


def test_la_cabecera_antigua_ya_no_autentica(cliente, servicio):
    admin = _crear(servicio, "admin@ejemplo.com", Rol.ADMIN)
    r = cliente.get("/usuarios", headers={"X-Usuario-Id": str(admin.id)})
    assert r.status_code == 401


def test_tras_cerrar_sesion_la_ruta_privada_se_rechaza(cliente, servicio):
    _crear(servicio, "admin@ejemplo.com", Rol.ADMIN)
    _entrar(cliente, "admin@ejemplo.com")
    assert cliente.get("/usuarios").status_code == 200
    cliente.post("/auth/logout")
    assert cliente.get("/usuarios").status_code == 401


def test_rutas_publicas_no_piden_sesion(cliente):
    assert cliente.get("/health").status_code == 200
    assert cliente.get("/").status_code == 200


# ---- Rutas de administrador ----
def test_listar_como_usuario_normal_devuelve_403(cliente, servicio):
    _crear(servicio, "ana@ejemplo.com")
    _entrar(cliente, "ana@ejemplo.com")
    assert cliente.get("/usuarios").status_code == 403


def test_listar_como_admin_devuelve_200(cliente, servicio):
    _crear(servicio, "admin@ejemplo.com", Rol.ADMIN)
    _crear(servicio, "ana@ejemplo.com")
    _entrar(cliente, "admin@ejemplo.com")
    r = cliente.get("/usuarios")
    assert r.status_code == 200 and len(r.json()) == 2


def test_consultar_activo_como_admin(cliente, servicio):
    _crear(servicio, "admin@ejemplo.com", Rol.ADMIN)
    ana = servicio.registrar("ana@ejemplo.com", CLAVE)  # pendiente
    _entrar(cliente, "admin@ejemplo.com")
    r = cliente.get(f"/usuarios/{ana.id}/activo")
    assert r.status_code == 200 and r.json() == {"activo": False}


def test_consultar_activo_como_usuario_normal_devuelve_403(cliente, servicio):
    ana = _crear(servicio, "ana@ejemplo.com")
    _entrar(cliente, "ana@ejemplo.com")
    assert cliente.get(f"/usuarios/{ana.id}/activo").status_code == 403


def test_usuario_normal_no_puede_eliminar_a_otro(cliente, servicio):
    _crear(servicio, "ana@ejemplo.com")
    luis = _crear(servicio, "luis@ejemplo.com")
    _entrar(cliente, "ana@ejemplo.com")
    assert cliente.delete(f"/usuarios/{luis.id}").status_code == 403


def test_usuario_puede_eliminar_su_propia_cuenta(cliente, servicio):
    ana = _crear(servicio, "ana@ejemplo.com")
    _entrar(cliente, "ana@ejemplo.com")
    assert cliente.delete(f"/usuarios/{ana.id}").status_code == 204


def test_admin_puede_eliminar_a_otro_usuario(cliente, servicio):
    _crear(servicio, "admin@ejemplo.com", Rol.ADMIN)
    luis = _crear(servicio, "luis@ejemplo.com")
    _entrar(cliente, "admin@ejemplo.com")
    assert cliente.delete(f"/usuarios/{luis.id}").status_code == 204


def test_usuario_eliminado_pierde_el_acceso(cliente, servicio):
    ana = _crear(servicio, "ana@ejemplo.com")
    _entrar(cliente, "ana@ejemplo.com")
    cliente.delete(f"/usuarios/{ana.id}")
    assert cliente.get("/auth/sesion").status_code == 401

def test_el_listado_incluye_a_los_eliminados_con_su_estado(cliente, servicio):
    _crear(servicio, "admin@ejemplo.com", Rol.ADMIN)
    luis = _crear(servicio, "luis@ejemplo.com")
    _entrar(cliente, "admin@ejemplo.com")
    cliente.delete(f"/usuarios/{luis.id}")
    estados = {u["email"]: u["estado"] for u in cliente.get("/usuarios").json()}
    assert estados["luis@ejemplo.com"] == "eliminado"


def test_una_cuenta_eliminada_no_puede_volver_a_iniciar_sesion(cliente, servicio):
    ana = _crear(servicio, "ana@ejemplo.com")
    _entrar(cliente, "ana@ejemplo.com")
    cliente.delete(f"/usuarios/{ana.id}")
    r = cliente.post("/auth/login", json={"email": "ana@ejemplo.com", "password": CLAVE})
    assert r.status_code == 403
