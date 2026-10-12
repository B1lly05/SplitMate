"""Los mismos contratos se exigen a la implementación en memoria y a la de MongoDB.
Para MongoDB se usa mongomock, así que no hace falta una base de datos real."""
from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from back.datos.memoria import RepositorioMemoria
from back.datos.mongo import RepositorioSesionesMongo, RepositorioUsuariosMongo
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.logica.auth import ServicioAuth
from back.logica.errores import CredencialesInvalidas, EmailDuplicado, NoAutenticado
from back.logica.modelos import Estado, Rol
from back.logica.servicio import ServicioUsuarios
from back.logica.sesiones import Sesion


@pytest.fixture(params=["memoria", "mongo"])
def repo(request):
    if request.param == "memoria":
        return RepositorioMemoria()
    return RepositorioUsuariosMongo(mongomock.MongoClient()["pruebas"])


@pytest.fixture(params=["memoria", "mongo"])
def repo_sesiones(request):
    if request.param == "memoria":
        return RepositorioSesionesMemoria()
    return RepositorioSesionesMongo(mongomock.MongoClient()["pruebas"])


def test_crear_asigna_ids_consecutivos(repo):
    a = repo.crear("a@ejemplo.com", Rol.USUARIO, Estado.PENDIENTE)
    b = repo.crear("b@ejemplo.com", Rol.USUARIO, Estado.PENDIENTE)
    assert (a.id, b.id) == (1, 2)


def test_crear_guarda_todos_los_campos(repo):
    u = repo.crear("a@ejemplo.com", Rol.ADMIN, Estado.ACTIVO, "hash-x")
    leido = repo.obtener_por_id(u.id)
    assert (leido.email, leido.rol, leido.estado, leido.password_hash) == (
        "a@ejemplo.com", Rol.ADMIN, Estado.ACTIVO, "hash-x")


def test_obtener_por_email_y_por_id(repo):
    u = repo.crear("a@ejemplo.com", Rol.USUARIO, Estado.PENDIENTE)
    assert repo.obtener_por_email("a@ejemplo.com").id == u.id
    assert repo.obtener_por_email("otro@ejemplo.com") is None
    assert repo.obtener_por_id(999) is None


def test_el_email_es_unico_en_el_repositorio(repo):
    repo.crear("a@ejemplo.com", Rol.USUARIO, Estado.PENDIENTE)
    with pytest.raises(EmailDuplicado):
        repo.crear("a@ejemplo.com", Rol.USUARIO, Estado.PENDIENTE)


def test_listar_devuelve_todos_en_orden(repo):
    repo.crear("a@ejemplo.com", Rol.USUARIO, Estado.PENDIENTE)
    repo.crear("b@ejemplo.com", Rol.USUARIO, Estado.PENDIENTE)
    assert [u.email for u in repo.listar()] == ["a@ejemplo.com", "b@ejemplo.com"]


def test_actualizar_persiste_los_cambios(repo):
    u = repo.crear("a@ejemplo.com", Rol.USUARIO, Estado.PENDIENTE)
    u.estado = Estado.ELIMINADO
    repo.actualizar(u)
    assert repo.obtener_por_id(u.id).estado == Estado.ELIMINADO


def test_sesion_guardar_obtener_y_eliminar(repo_sesiones):
    expira = datetime.now(timezone.utc) + timedelta(hours=1)
    repo_sesiones.guardar(Sesion("token-1", 7, expira))
    leida = repo_sesiones.obtener("token-1")
    assert leida.id_usuario == 7 and leida.expira_en > datetime.now(timezone.utc)
    repo_sesiones.eliminar("token-1")
    assert repo_sesiones.obtener("token-1") is None


def test_sesion_inexistente_devuelve_none(repo_sesiones):
    assert repo_sesiones.obtener("no-existe") is None


def test_mongo_no_guarda_el_token_en_claro():
    base = mongomock.MongoClient()["pruebas"]
    repo = RepositorioSesionesMongo(base)
    repo.guardar(Sesion("token-secreto", 1, datetime.now(timezone.utc) + timedelta(hours=1)))
    guardado = base["sesiones"].find_one()
    assert "token-secreto" not in str(guardado)


# ---- La lógica funciona igual sobre MongoDB, sin modificarla ----
@pytest.fixture
def pila_mongo():
    base = mongomock.MongoClient()["pruebas"]
    usuarios = ServicioUsuarios(RepositorioUsuariosMongo(base))
    return usuarios, ServicioAuth(usuarios, RepositorioSesionesMongo(base))


def test_flujo_completo_de_usuario_sobre_mongodb(pila_mongo):
    usuarios, auth = pila_mongo
    ana = usuarios.registrar("ana@ejemplo.com", "clave-segura-1")
    ana.estado = Estado.ACTIVO
    usuarios.repositorio.actualizar(ana)

    token, _ = auth.login("ana@ejemplo.com", "clave-segura-1")
    assert auth.usuario_de_sesion(token).id == ana.id

    auth.logout(token)
    with pytest.raises(NoAutenticado):
        auth.usuario_de_sesion(token)

    usuarios.eliminar(ana, ana.id)
    with pytest.raises(CredencialesInvalidas):
        auth.login("ana@ejemplo.com", "otra-clave-1")


def test_registrar_duplicado_sobre_mongodb_falla(pila_mongo):
    usuarios, _ = pila_mongo
    usuarios.registrar("ana@ejemplo.com", "clave-segura-1")
    with pytest.raises(EmailDuplicado):
        usuarios.registrar("ana@ejemplo.com", "clave-segura-2")