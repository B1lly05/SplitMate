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
        cuerpo = {
            "sender": {"name": self._nombre, "email": self._remitente},
            "to": [{"email": destinatario}],
            "subject": "Confirma tu cuenta de SplitMate",
            "htmlContent": (
                "<html><body>"
                "<p>Hola,</p>"
                "<p>Para activar tu cuenta de SplitMate pulsa en este enlace "
                "(caduca en 24 horas):</p>"
                f'<p><a href="{enlace_html}">Confirmar mi cuenta</a></p>'
                f"<p>Si el botón no funciona, copia esta dirección en tu navegador:<br>{enlace_html}</p>"
                "<p>Si no has creado tú esta cuenta, ignora este mensaje.</p>"
                "</body></html>"
            ),
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
