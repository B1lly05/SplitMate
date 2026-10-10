import re

from back.logica.errores import (
    CuentaNoDisponible,
    DatosInvalidos,
    EmailDuplicado,
    NoAutorizado,
    UsuarioNoEncontrado,
    NoAutenticado
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

    def eliminar(self, solicitante: Usuario, id_usuario: int) -> None:
        """El admin elimina a cualquiera; un usuario normal solo a sí mismo."""
        if solicitante.rol != Rol.ADMIN and solicitante.id != id_usuario:
            raise NoAutorizado("Solo puedes eliminar tu propia cuenta")
        objetivo = self.repositorio.obtener_por_id(id_usuario)
        if objetivo is None or objetivo.estado == Estado.ELIMINADO:
            raise UsuarioNoEncontrado("El usuario no existe")
        objetivo.estado = Estado.ELIMINADO
        self.repositorio.actualizar(objetivo)

    def comprobar_acceso(self, email: str) -> Usuario:
        """Comprueba si una cuenta puede iniciar sesión (se usará en el login)."""
        usuario = self.repositorio.obtener_por_email(email.strip().lower())
        if usuario is None:
            raise UsuarioNoEncontrado("El usuario no existe")
        if usuario.estado == Estado.ELIMINADO:
            raise CuentaNoDisponible("La cuenta ha sido eliminada")
        if usuario.estado == Estado.PENDIENTE:
            raise CuentaNoDisponible("Debes confirmar tu correo antes de iniciar sesión")
        return usuario    
    def identificar(self, id_usuario) -> Usuario:
        """Devuelve el usuario que hace la petición, o falla si no es válido."""
        if id_usuario is None:
            raise NoAutenticado("Hay que identificarse")
        usuario = self.repositorio.obtener_por_id(id_usuario)
        if usuario is None or usuario.estado == Estado.ELIMINADO:
            raise NoAutenticado("Usuario no válido")
        return usuario