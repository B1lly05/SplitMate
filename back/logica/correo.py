from abc import ABC, abstractmethod


class ErrorEnvio(Exception):
    """No se pudo entregar el correo al servicio de envío."""


class EnviadorCorreo(ABC):
    """Contrato que define la lógica; el servicio concreto (Brevo, simulado...) vive
    fuera, en back/externos."""

    @abstractmethod
    def enviar_confirmacion(self, destinatario: str, enlace: str) -> None:
        """Envía el correo con el enlace de confirmación. Lanza ErrorEnvio si falla."""

    @abstractmethod
    def enviar_recordatorio(self, destinatario: str, de: str, grupo: str, importe: int,
                            enlace: str) -> None:
        """Avisa a quien debe dinero (importe en céntimos) de parte de otra persona del
        grupo. Lanza ErrorEnvio si falla."""

    @abstractmethod
    def enviar_invitacion(self, destinatario: str, de: str, grupo: str, enlace: str) -> None:
        """Invita a alguien sin cuenta a unirse a un grupo. Lanza ErrorEnvio si falla."""
