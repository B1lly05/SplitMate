import re

from back.logica.errores import (
    DatosInvalidos,
    EmailDuplicado,
    NoAutorizado,
    UsuarioNoEncontrado,
)
from back.logica.modelos import Estado, Rol, Usuario
from back.logica.repositorio import RepositorioUsuarios

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ServicioUsuarios:
    def __init__(self, repositorio: RepositorioUsuarios):
        self.repositorio = repositorio

    def _exigir_admin(self, solicitante: Usuario) -> None:
        if solicitante.rol != Rol.ADMIN:
            raise NoAutorizado("Solo el administrador puede hacer esta operación")

    def alta(self, email: str, rol: Rol = Rol.USUARIO) -> Usuario:
        email = email.strip().lower()
        if not PATRON_EMAIL.match(email):
            raise DatosInvalidos("El email no tiene un formato válido")
        if self.repositorio.obtener_por_email(email):
            raise EmailDuplicado("Ya existe un usuario con ese email")
        return self.repositorio.crear(email, rol, Estado.PENDIENTE)

    def listar(self, solicitante: Usuario) -> list[Usuario]:
        self._exigir_admin(solicitante)
        return self.repositorio.listar()

    def esta_activo(self, solicitante: Usuario, id_usuario: int) -> bool:
        """Activo = cuenta confirmada (o creada por OAuth) y no eliminada.
        No indica si el usuario está conectado en este momento."""
        self._exigir_admin(solicitante)
        usuario = self.repositorio.obtener_por_id(id_usuario)
        if usuario is None:
            raise UsuarioNoEncontrado("El usuario no existe")
        return usuario.estado == Estado.ACTIVO