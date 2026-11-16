"""Cliente del proveedor externo GitHub (OAuth). Vive fuera de la lógica de negocio:
la lógica solo recibe un email ya verificado, nunca habla con GitHub."""
from typing import Optional
from urllib.parse import urlencode

import httpx

URL_AUTORIZACION = "https://github.com/login/oauth/authorize"
URL_TOKEN = "https://github.com/login/oauth/access_token"
URL_EMAILS = "https://api.github.com/user/emails"


class ErrorProveedor(Exception):
    """GitHub ha fallado o ha rechazado el código."""


class SinEmailVerificado(Exception):
    """La cuenta de GitHub no tiene ningún correo verificado."""


class ProveedorGitHub:
    def __init__(self, client_id: str, client_secret: str,
                 cliente: Optional[httpx.Client] = None):
        self._client_id = client_id
        self._client_secret = client_secret
        # Se puede inyectar un cliente (en las pruebas, con httpx.MockTransport)
        self._cliente = cliente or httpx.Client(timeout=10)

    def configurado(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def url_autorizacion(self, state: str, redirect_uri: str) -> str:
        """URL a la que se redirige al usuario. El secreto nunca viaja aquí."""
        parametros = urlencode({
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "scope": "user:email",
            "state": state,
        })
        return f"{URL_AUTORIZACION}?{parametros}"

    def obtener_email_verificado(self, code: str, redirect_uri: str) -> str:
        try:
            token = self._canjear_codigo(code, redirect_uri)
            return self._email_verificado(token)
        except httpx.HTTPError as error:
            raise ErrorProveedor("No se pudo hablar con GitHub") from error

    def _canjear_codigo(self, code: str, redirect_uri: str) -> str:
        r = self._cliente.post(
            URL_TOKEN,
            headers={"Accept": "application/json"},
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        if r.status_code != 200:
            raise ErrorProveedor("GitHub rechazó la petición del token")
        try:
            token = r.json().get("access_token")
        except ValueError:
            raise ErrorProveedor("Respuesta de GitHub no válida")
        if not token:
            raise ErrorProveedor("GitHub no ha dado un token (código no válido)")
        return token

    def _email_verificado(self, token: str) -> str:
        r = self._cliente.get(
            URL_EMAILS,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "SplitMate",
            },
        )
        if r.status_code != 200:
            raise ErrorProveedor("GitHub no devolvió los correos")
        try:
            correos = r.json()
        except ValueError:
            raise ErrorProveedor("Respuesta de GitHub no válida")
        if not isinstance(correos, list):
            raise ErrorProveedor("Respuesta de GitHub no válida")
        verificados = [c for c in correos
                       if isinstance(c, dict) and c.get("verified") and c.get("email")]
        if not verificados:
            raise SinEmailVerificado("La cuenta de GitHub no tiene correo verificado")
        principal = next((c for c in verificados if c.get("primary")), verificados[0])
        return principal["email"]
