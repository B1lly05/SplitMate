"""Envío de correo con Brevo (API HTTPS: en Cloud Run el SMTP directo suele estar bloqueado)."""
import html
import logging
from typing import Optional

import httpx

from back.logica.correo import EnviadorCorreo, ErrorEnvio

log = logging.getLogger("splitmate.correo")

URL_ENVIO = "https://api.brevo.com/v3/smtp/email"


class EnviadorBrevo(EnviadorCorreo):
    def __init__(self, api_key: str, remitente: str, nombre: str = "SplitMate",
                 cliente: Optional[httpx.Client] = None):
        self._api_key = api_key
        self._remitente = remitente
        self._nombre = nombre
        self._cliente = cliente or httpx.Client(timeout=10)

    def enviar_confirmacion(self, destinatario: str, enlace: str) -> None:
        enlace_html = html.escape(enlace, quote=True)
        self._enviar(destinatario, "Confirma tu cuenta de SplitMate", (
            "<p>Hola,</p>"
            "<p>Para activar tu cuenta de SplitMate pulsa en este enlace "
            "(caduca en 24 horas):</p>"
            f'<p><a href="{enlace_html}">Confirmar mi cuenta</a></p>'
            f"<p>Si el botón no funciona, copia esta dirección en tu navegador:<br>{enlace_html}</p>"
            "<p>Si no has creado tú esta cuenta, ignora este mensaje.</p>"
        ))

    def enviar_recordatorio(self, destinatario: str, de: str, grupo: str, importe: int,
                            enlace: str) -> None:
        # Todo lo que escribe una persona (email, nombre del grupo) se escapa antes de ir al HTML
        cantidad = f"{importe / 100:.2f}".replace(".", ",")
        self._enviar(destinatario, "Recordatorio de pago en SplitMate", (
            "<p>Hola,</p>"
            f"<p><strong>{html.escape(de)}</strong> te recuerda que le debes "
            f"<strong>{cantidad} €</strong> en el grupo «{html.escape(grupo)}».</p>"
            f'<p>Puedes ver el detalle y marcar el pago en <a href="{html.escape(enlace, quote=True)}">SplitMate</a>.</p>'
            "<p>Si ya lo has pagado, avisa a esa persona para que lo registre.</p>"
        ))

    def enviar_invitacion(self, destinatario: str, de: str, grupo: str, enlace: str) -> None:
        self._enviar(destinatario, "Te han invitado a un grupo en SplitMate", (
            "<p>Hola,</p>"
            f"<p><strong>{html.escape(de)}</strong> te ha invitado al grupo "
            f"«{html.escape(grupo)}» en SplitMate para repartir gastos.</p>"
            f'<p>Crea tu cuenta en <a href="{html.escape(enlace, quote=True)}">SplitMate</a> '
            "<strong>con este mismo correo</strong> (también vale entrar con GitHub si usa este email) "
            "y el grupo aparecerá automáticamente. La invitación caduca en 14 días.</p>"
            "<p>Si no conoces a esta persona, ignora este mensaje.</p>"
        ))

    def _enviar(self, destinatario: str, asunto: str, contenido_html: str) -> None:
        cuerpo = {
            "sender": {"name": self._nombre, "email": self._remitente},
            "to": [{"email": destinatario}],
            "subject": asunto,
            "htmlContent": f"<html><body>{contenido_html}</body></html>",
        }
        try:
            r = self._cliente.post(
                URL_ENVIO,
                headers={"api-key": self._api_key, "accept": "application/json"},
                json=cuerpo,
            )
        except httpx.HTTPError as error:
            log.error("No se pudo contactar con Brevo")
            raise ErrorEnvio("No se pudo contactar con Brevo") from error
        if r.status_code not in (200, 201):
            # Se registra el motivo que da Brevo (p. ej. remitente no verificado) para
            # poder diagnosticarlo; nunca la clave ni el enlace.
            try:
                datos = r.json()
                motivo = f"{datos.get('code', '')}: {str(datos.get('message', ''))[:200]}"
            except ValueError:
                motivo = "respuesta sin JSON"
            log.error("Brevo rechazó el envío: estado=%s %s", r.status_code, motivo)
            raise ErrorEnvio(f"Brevo rechazó el envío ({r.status_code})")
