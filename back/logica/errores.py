class ErrorDeNegocio(Exception):
    """Error de una regla de negocio."""


class EmailDuplicado(ErrorDeNegocio):
    pass


class DatosInvalidos(ErrorDeNegocio):
    pass