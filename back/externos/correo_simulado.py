"""Enviador que no envía nada: se usa en las pruebas y cuando no hay servicio configurado."""
import logging

from back.logica.correo import EnviadorCorreo, ErrorEnvio

log = logging.getLogger("splitmate.correo")


class EnviadorSimulado(EnviadorCorreo):
    def __init__(self, fallar: bool = False, avisar: bool = False):
        self.enviados: list[tuple[str, str]] = []  # (destinatario, enlace)
        self.fallar = fallar
        self._avisar = avisar

    def enviar_confirmacion(self, destinatario: str, enlace: str) -> None:
        if self.fallar:
            raise ErrorEnvio("Fallo simulado")
        if self._avisar:
            # Nunca se escribe el enlace en el log: lleva el token de confirmación
            log.warning("Correo NO enviado: servicio de correo sin configurar")
        self.enviados.append((destinatario, enlace))
