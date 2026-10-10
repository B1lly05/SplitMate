class ErrorDeNegocio(Exception):
    """Error de una regla de negocio."""


class EmailDuplicado(ErrorDeNegocio):
    pass


class DatosInvalidos(ErrorDeNegocio):
    pass


class NoAutorizado(ErrorDeNegocio):
    pass


class UsuarioNoEncontrado(ErrorDeNegocio):
    pass

class CuentaNoDisponible(ErrorDeNegocio):
    pass
class NoAutenticado(ErrorDeNegocio):
    pass