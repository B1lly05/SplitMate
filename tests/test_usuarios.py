import pytest

from back.datos.memoria import RepositorioMemoria
from back.logica.errores import DatosInvalidos, EmailDuplicado
from back.logica.modelos import Estado, Rol
from back.logica.servicio import ServicioUsuarios


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