from abc import ABC, abstractmethod


class ErrorEnvio(Exception):
    """No se pudo entregar el correo al servicio de envío."""


class EnviadorCorreo(ABC):
    """Contrato que define la lógica; el servicio concreto (Brevo, simulado...) vive
    fuera, en back/externos."""

    @abstractmethod
    def enviar_confirmacion(self, destinatario: str, enlace: str) -> None:
        """Envía el correo con el enlace de confirmación. Lanza ErrorEnvio si falla."""
