import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable

from back.logica.correo import EnviadorCorreo, ErrorEnvio
from back.logica.errores import TokenInvalido
from back.logica.modelos import Estado, Usuario
from back.logica.servicio import ServicioUsuarios
from back.logica.tokens import RepositorioTokens, TokenConfirmacion

log = logging.getLogger("splitmate.confirmacion")

MENSAJE_TOKEN_INVALIDO = "El enlace no es válido o ha caducado"


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _clave(token: str) -> str:
    # Solo se guarda el hash: si se filtrara la base de datos, los enlaces
    # pendientes no se podrían reconstruir.
    return hashlib.sha256(token.encode()).hexdigest()


class ServicioConfirmacion:
    def __init__(self, usuarios: ServicioUsuarios, tokens: RepositorioTokens,
                 enviador: EnviadorCorreo, base_url: str,
                 duracion: timedelta = timedelta(hours=24),
                 espera_reenvio: timedelta = timedelta(seconds=60),
                 reloj: Callable[[], datetime] = _ahora):
        self.usuarios = usuarios
        self.tokens = tokens
        self.enviador = enviador
        self.base_url = base_url.rstrip("/")
        self.duracion = duracion
        self.espera_reenvio = espera_reenvio
        self.reloj = reloj

    def enviar_si_pendiente(self, usuario: Usuario) -> bool:
        """Genera un token nuevo (anulando el anterior) y envía el correo.
        Devuelve True si se ha enviado. Un fallo de envío no rompe el registro."""
        if usuario.estado != Estado.PENDIENTE:
            return False
        self.tokens.eliminar_de_usuario(usuario.id)
        token = secrets.token_urlsafe(32)
        ahora = self.reloj()
        registro = TokenConfirmacion(_clave(token), usuario.id, ahora, ahora + self.duracion)
        self.tokens.guardar(registro)
        enlace = f"{self.base_url}/?confirmar={token}"
        try:
            self.enviador.enviar_confirmacion(usuario.email, enlace)
        except ErrorEnvio:
            self.tokens.eliminar(registro.clave)
            log.error("No se pudo enviar el correo de confirmación id=%s", usuario.id)
            return False
        log.info("Correo de confirmación enviado id=%s", usuario.id)
        return True

    def confirmar(self, token: str) -> Usuario:
        """Activa la cuenta con un token válido. Cada token vale una sola vez."""
        registro = self.tokens.obtener(_clave(token)) if token else None
        if registro is None:
            log.warning("Confirmación rechazada: token desconocido")
            raise TokenInvalido(MENSAJE_TOKEN_INVALIDO)
        if registro.expira_en <= self.reloj():
            self.tokens.eliminar(registro.clave)
            log.warning("Confirmación rechazada: token caducado id=%s", registro.id_usuario)
            raise TokenInvalido(MENSAJE_TOKEN_INVALIDO)
        usuario = self.usuarios.repositorio.obtener_por_id(registro.id_usuario)
        if usuario is None or usuario.estado == Estado.ELIMINADO:
            self.tokens.eliminar(registro.clave)
            log.warning("Confirmación rechazada: cuenta no disponible id=%s", registro.id_usuario)
            raise TokenInvalido(MENSAJE_TOKEN_INVALIDO)
        if usuario.estado == Estado.PENDIENTE:
            usuario.estado = Estado.ACTIVO
            self.usuarios.repositorio.actualizar(usuario)
        self.tokens.eliminar(registro.clave)
        log.info("Cuenta confirmada id=%s", usuario.id)
        return usuario

    def reenviar(self, email: str) -> None:
        """Reenvía el correo si hay una cuenta local pendiente con ese email. No dice
        nada de si existe o no (quien llama responde siempre lo mismo), y respeta una
        espera mínima entre envíos para que no se use para llenar un buzón."""
        usuario = self.usuarios.repositorio.obtener_por_email(email.strip().lower())
        if (usuario is None or usuario.estado != Estado.PENDIENTE
                or usuario.password_hash is None):
            log.info("Reenvío ignorado: no hay cuenta pendiente que confirmar")
            return
        reciente = self.tokens.obtener_de_usuario(usuario.id)
        if reciente is not None and self.reloj() - reciente.creado_en < self.espera_reenvio:
            log.info("Reenvío ignorado: correo enviado hace poco id=%s", usuario.id)
            return
        self.enviar_si_pendiente(usuario)
