import pytest

from back.datos.memoria import RepositorioMemoria
from back.logica.errores import DatosInvalidos, EmailDuplicado
from back.logica.modelos import Estado, Rol
from back.logica.servicio import ServicioUsuarios
from back.logica.errores import NoAutorizado,UsuarioNoEncontrado,CuentaNoDisponible

@pytest.fixture
def servicio():
    return ServicioUsuarios(RepositorioMemoria())


def test_alta_crea_usuario_pendiente(servicio):
    usuario = servicio.alta("ana@ejemplo.com")
    assert usuario.estado == Estado.PENDIENTE
    assert usuario.rol == Rol.USUARIO


def test_alta_normaliza_el_email(servicio):
    usuario = servicio.alta("  Ana@Ejemplo.COM ")
    assert usuario.email == "ana@ejemplo.com"


def test_alta_con_email_duplicado_falla(servicio):
    servicio.alta("ana@ejemplo.com")
    with pytest.raises(EmailDuplicado):
        servicio.alta("ana@ejemplo.com")


def test_alta_con_email_invalido_falla(servicio):
    with pytest.raises(DatosInvalidos):
        servicio.alta("esto-no-es-un-email")

def _crear_admin(servicio):
    return servicio.alta("admin@ejemplo.com", Rol.ADMIN)


def test_admin_puede_listar_usuarios(servicio):
    admin = _crear_admin(servicio)
    servicio.alta("ana@ejemplo.com")
    emails = [u.email for u in servicio.listar(admin)]
    assert "ana@ejemplo.com" in emails


def test_usuario_normal_no_puede_listar(servicio):
    normal = servicio.alta("ana@ejemplo.com")
    with pytest.raises(NoAutorizado):
        servicio.listar(normal)


def test_usuario_pendiente_no_esta_activo(servicio):
    admin = _crear_admin(servicio)
    pendiente = servicio.alta("ana@ejemplo.com")
    assert servicio.esta_activo(admin, pendiente.id) is False


def test_usuario_confirmado_esta_activo(servicio):
    admin = _crear_admin(servicio)
    usuario = servicio.alta("ana@ejemplo.com")
    usuario.estado = Estado.ACTIVO
    servicio.repositorio.actualizar(usuario)
    assert servicio.esta_activo(admin, usuario.id) is True


def test_esta_activo_de_usuario_inexistente_falla(servicio):
    admin = _crear_admin(servicio)
    with pytest.raises(UsuarioNoEncontrado):
        servicio.esta_activo(admin, 999)


def test_usuario_normal_no_puede_consultar_si_esta_activo(servicio):
    normal = servicio.alta("ana@ejemplo.com")
    with pytest.raises(NoAutorizado):
        servicio.esta_activo(normal, normal.id)
def _activar(servicio, usuario):
    usuario.estado = Estado.ACTIVO
    servicio.repositorio.actualizar(usuario)
    return usuario


def test_admin_puede_eliminar_a_otro_usuario(servicio):
    admin = _crear_admin(servicio)
    ana = servicio.alta("ana@ejemplo.com")
    servicio.eliminar(admin, ana.id)
    assert servicio.repositorio.obtener_por_id(ana.id).estado == Estado.ELIMINADO


def test_usuario_puede_eliminar_su_propia_cuenta(servicio):
    ana = servicio.alta("ana@ejemplo.com")
    servicio.eliminar(ana, ana.id)
    assert servicio.repositorio.obtener_por_id(ana.id).estado == Estado.ELIMINADO


def test_usuario_normal_no_puede_eliminar_a_otro(servicio):
    ana = servicio.alta("ana@ejemplo.com")
    luis = servicio.alta("luis@ejemplo.com")
    with pytest.raises(NoAutorizado):
        servicio.eliminar(ana, luis.id)
    assert servicio.repositorio.obtener_por_id(luis.id).estado != Estado.ELIMINADO


def test_eliminar_usuario_inexistente_falla(servicio):
    admin = _crear_admin(servicio)
    with pytest.raises(UsuarioNoEncontrado):
        servicio.eliminar(admin, 999)


def test_eliminar_dos_veces_falla(servicio):
    admin = _crear_admin(servicio)
    ana = servicio.alta("ana@ejemplo.com")
    servicio.eliminar(admin, ana.id)
    with pytest.raises(UsuarioNoEncontrado):
        servicio.eliminar(admin, ana.id)


def test_usuario_eliminado_no_puede_acceder(servicio):
    admin = _crear_admin(servicio)
    ana = _activar(servicio, servicio.alta("ana@ejemplo.com"))
    servicio.eliminar(admin, ana.id)
    with pytest.raises(CuentaNoDisponible):
        servicio.comprobar_acceso("ana@ejemplo.com")


def test_usuario_pendiente_no_puede_acceder(servicio):
    servicio.alta("ana@ejemplo.com")
    with pytest.raises(CuentaNoDisponible):
        servicio.comprobar_acceso("ana@ejemplo.com")


def test_usuario_activo_puede_acceder(servicio):
    ana = _activar(servicio, servicio.alta("ana@ejemplo.com"))
    assert servicio.comprobar_acceso("ana@ejemplo.com").id == ana.id