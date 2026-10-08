import pytest

from back.datos.memoria import RepositorioMemoria
from back.logica.errores import DatosInvalidos, EmailDuplicado
from back.logica.modelos import Estado, Rol
from back.logica.servicio import ServicioUsuarios
from back.logica.errores import NoAutorizado,UsuarioNoEncontrado

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