import httpx
import pytest

from back.externos.github import ErrorProveedor, ProveedorGitHub, SinEmailVerificado

REDIRECT = "http://127.0.0.1:8000/auth/github/callback"


def _proveedor(manejador):
    cliente = httpx.Client(transport=httpx.MockTransport(manejador))
    return ProveedorGitHub("id-publico", "secreto-privado", cliente)


def _github(correos, token="tok", estado_token=200, estado_correos=200):
    def manejador(peticion: httpx.Request):
        if peticion.url.host == "github.com":
            cuerpo = {"access_token": token} if token else {"error": "bad_verification_code"}
            return httpx.Response(estado_token, json=cuerpo)
        assert peticion.headers["Authorization"] == "Bearer tok"
        return httpx.Response(estado_correos, json=correos)
    return manejador


def test_la_url_de_autorizacion_no_lleva_el_secreto():
    url = _proveedor(_github([])).url_autorizacion("estado-1", REDIRECT)
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=id-publico" in url and "state=estado-1" in url
    assert "secreto-privado" not in url


def test_sin_credenciales_no_esta_configurado():
    assert not ProveedorGitHub("", "").configurado()
    assert _proveedor(_github([])).configurado()


def test_elige_el_correo_principal_verificado():
    correos = [
        {"email": "otro@ej.com", "primary": False, "verified": True},
        {"email": "sin@ej.com", "primary": False, "verified": False},
        {"email": "principal@ej.com", "primary": True, "verified": True},
    ]
    assert _proveedor(_github(correos)).obtener_email_verificado("c", REDIRECT) == "principal@ej.com"


def test_si_el_principal_no_esta_verificado_usa_otro_verificado():
    correos = [
        {"email": "principal@ej.com", "primary": True, "verified": False},
        {"email": "otro@ej.com", "primary": False, "verified": True},
    ]
    assert _proveedor(_github(correos)).obtener_email_verificado("c", REDIRECT) == "otro@ej.com"


def test_sin_correo_verificado_falla():
    correos = [{"email": "a@ej.com", "primary": True, "verified": False}]
    with pytest.raises(SinEmailVerificado):
        _proveedor(_github(correos)).obtener_email_verificado("c", REDIRECT)


def test_codigo_rechazado_por_github_falla():
    with pytest.raises(ErrorProveedor):
        _proveedor(_github([], token=None)).obtener_email_verificado("malo", REDIRECT)


def test_error_http_al_pedir_correos_falla():
    with pytest.raises(ErrorProveedor):
        _proveedor(_github([], estado_correos=500)).obtener_email_verificado("c", REDIRECT)


def test_un_fallo_de_red_se_convierte_en_error_del_proveedor():
    def caido(peticion):
        raise httpx.ConnectError("sin red")
    with pytest.raises(ErrorProveedor):
        _proveedor(caido).obtener_email_verificado("c", REDIRECT)
