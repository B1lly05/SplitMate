import mongomock
import pytest

from back.datos.memoria import RepositorioMemoria
from back.datos.mongo import RepositorioSesionesMongo, RepositorioUsuariosMongo
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.logica.auth import ServicioAuth
from back.logica.errores import CredencialesInvalidas, CuentaNoDisponible, DatosInvalidos
from back.logica.modelos import Estado, Rol
from back.logica.servicio import ServicioUsuarios


@pytest.fixture(params=["memoria", "mongo"])
def pila(request):
    if request.param == "memoria":
        usuarios = ServicioUsuarios(RepositorioMemoria())
        return usuarios, ServicioAuth(usuarios, RepositorioSesionesMemoria())
    base = mongomock.MongoClient()["pruebas"]
    usuarios = ServicioUsuarios(RepositorioUsuariosMongo(base))
    return usuarios, ServicioAuth(usuarios, RepositorioSesionesMongo(base))


def test_un_usuario_nuevo_se_crea_activo_sin_contrasena_y_como_usuario(pila):
    usuarios, _ = pila
    u = usuarios.acceso_externo("Nuevo@Ejemplo.com")
    assert u.email == "nuevo@ejemplo.com"
    assert u.estado == Estado.ACTIVO and u.rol == Rol.USUARIO
    assert u.password_hash is None


def test_un_usuario_existente_activo_entra_sin_duplicarse(pila):
    usuarios, _ = pila
    original = usuarios.registrar("ana@ejemplo.com", "clave-segura-1")
    original.estado = Estado.ACTIVO
    usuarios.repositorio.actualizar(original)
    u = usuarios.acceso_externo("ana@ejemplo.com")
    assert u.id == original.id
    assert len(usuarios.repositorio.listar()) == 1


def test_una_cuenta_pendiente_se_activa_y_pierde_la_contrasena_local(pila):
    usuarios, auth = pila
    usuarios.registrar("ana@ejemplo.com", "clave-del-impostor")  # pendiente
    u = usuarios.acceso_externo("ana@ejemplo.com")
    assert u.estado == Estado.ACTIVO and u.password_hash is None
    with pytest.raises(CredencialesInvalidas):
        auth.login("ana@ejemplo.com", "clave-del-impostor")


def test_una_cuenta_eliminada_no_puede_volver_a_entrar(pila):
    usuarios, _ = pila
    u = usuarios.acceso_externo("ana@ejemplo.com")
    u.estado = Estado.ELIMINADO
    usuarios.repositorio.actualizar(u)
    with pytest.raises(CuentaNoDisponible):
        usuarios.acceso_externo("ana@ejemplo.com")


def test_el_acceso_externo_nunca_crea_administradores(pila):
    usuarios, _ = pila
    assert usuarios.acceso_externo("admin@ejemplo.com").rol == Rol.USUARIO


def test_un_correo_invalido_se_rechaza(pila):
    usuarios, _ = pila
    with pytest.raises(DatosInvalidos):
        usuarios.acceso_externo("no-es-un-correo")
    assert usuarios.repositorio.listar() == []


def test_login_externo_abre_una_sesion_valida(pila):
    usuarios, auth = pila
    token, u = auth.login_externo("ana@ejemplo.com")
    assert auth.usuario_de_sesion(token).id == u.id


def test_un_usuario_solo_oauth_no_puede_entrar_con_contrasena(pila):
    _, auth = pila
    auth.login_externo("ana@ejemplo.com")
    with pytest.raises(CredencialesInvalidas):
        auth.login("ana@ejemplo.com", "cualquier-clave-1")


def test_un_administrador_conserva_su_rol_al_entrar_por_oauth(pila):
    usuarios, auth = pila
    usuarios.crear_admin_inicial("admin@ejemplo.com", "clave-admin-1")
    _, u = auth.login_externo("admin@ejemplo.com")
    assert u.rol == Rol.ADMIN
