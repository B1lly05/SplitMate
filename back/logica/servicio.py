import re

from back.logica.errores import DatosInvalidos, EmailDuplicado
from back.logica.modelos import Estado, Rol, Usuario
from back.logica.repositorio import RepositorioUsuarios

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ServicioUsuarios:
    def __init__(self, repositorio: RepositorioUsuarios):
        self.repositorio = repositorio

    def alta(self, email: str, rol: Rol = Rol.USUARIO) -> Usuario:
        email = email.strip().lower()
        if not PATRON_EMAIL.match(email):
            raise DatosInvalidos("El email no tiene un formato válido")
        if self.repositorio.obtener_por_email(email):
            raise EmailDuplicado("Ya existe un usuario con ese email")
        return self.repositorio.crear(email, rol, Estado.PENDIENTE)