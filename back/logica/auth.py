import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from back.logica import seguridad
from back.logica.errores import CredencialesInvalidas, CuentaNoDisponible, NoAutenticado
from back.logica.modelos import Estado, Usuario
from back.logica.servicio import ServicioUsuarios
from back.logica.sesiones import RepositorioSesiones, Sesion


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class ServicioAuth:
    def __init__(self, usuarios: ServicioUsuarios, sesiones: RepositorioSesiones,
                 duracion: timedelta = timedelta(hours=8),
                 reloj: Callable[[], datetime] = _ahora):
        self.usuarios = usuarios
        self.sesiones = sesiones
        self.duracion = duracion
        self.reloj = reloj

    def login(self, email: str, password: str) -> tuple[str, Usuario]:
        usuario = self.usuarios.repositorio.obtener_por_email(email.strip().lower())
        # Mismo mensaje si el email no existe o la contraseña falla (no revela cuentas)
        if (usuario is None or usuario.password_hash is None
                or not seguridad.verificar(password, usuario.password_hash)):
            raise CredencialesInvalidas("Email o contraseña incorrectos")
        if usuario.estado == Estado.ELIMINADO:
            raise CuentaNoDisponible("La cuenta ha sido eliminada")
        if usuario.estado == Estado.PENDIENTE:
            raise CuentaNoDisponible("Debes confirmar tu correo antes de iniciar sesión")
        token = secrets.token_urlsafe(32)
        self.sesiones.guardar(Sesion(token, usuario.id, self.reloj() + self.duracion))
        return token, usuario

    def logout(self, token: str) -> None:
        self.sesiones.eliminar(token)

    def usuario_de_sesion(self, token: Optional[str]) -> Usuario:
        if not token:
            raise NoAutenticado("Hay que iniciar sesión")
        sesion = self.sesiones.obtener(token)
        if sesion is None:
            raise NoAutenticado("Sesión no válida")
        if sesion.expira_en <= self.reloj():
            self.sesiones.eliminar(token)
            raise NoAutenticado("La sesión ha caducado")
        return self.usuarios.identificar(sesion.id_usuario)