import json

import httpx
import pytest

from back.externos.brevo import EnviadorBrevo
from back.logica.correo import ErrorEnvio

ENLACE = "https://splitmate.ejemplo.com/?confirmar=tok_abc-123"


def _enviador(manejador):
    cliente = httpx.Client(transport=httpx.MockTransport(manejador))
    return EnviadorBrevo("clave-api-secreta", "no-reply@ejemplo.com", "SplitMate", cliente)


def test_envia_a_la_api_de_brevo_con_clave_remitente_y_enlace():
    recibidas = []

    def manejador(peticion: httpx.Request):
        recibidas.append(peticion)
        return httpx.Response(201, json={"messageId": "<x@y>"})

    _enviador(manejador).enviar_confirmacion("ana@ejemplo.com", ENLACE)
    peticion = recibidas[0]
    assert str(peticion.url) == "https://api.brevo.com/v3/smtp/email"
    assert peticion.headers["api-key"] == "clave-api-secreta"
    cuerpo = json.loads(peticion.content)
    assert cuerpo["sender"] == {"name": "SplitMate", "email": "no-reply@ejemplo.com"}
    assert cuerpo["to"] == [{"email": "ana@ejemplo.com"}]
    assert ENLACE in cuerpo["htmlContent"] and cuerpo["subject"]


def test_el_enlace_se_escapa_en_el_html():
    recibidas = []

    def manejador(peticion):
        recibidas.append(json.loads(peticion.content))
        return httpx.Response(201, json={})

    _enviador(manejador).enviar_confirmacion("ana@ejemplo.com", 'https://x/?a="><script>')
    assert "<script>" not in recibidas[0]["htmlContent"]


@pytest.mark.parametrize("estado", [400, 401, 403, 500])
def test_una_respuesta_de_error_lanza_error_de_envio(estado):
    manejador = lambda p: httpx.Response(estado, json={"code": "unauthorized", "message": "Key not found"})
    with pytest.raises(ErrorEnvio):
        _enviador(manejador).enviar_confirmacion("ana@ejemplo.com", ENLACE)


def test_un_fallo_de_red_lanza_error_de_envio():
    def caido(peticion):
        raise httpx.ConnectError("sin red")
    with pytest.raises(ErrorEnvio):
        _enviador(caido).enviar_confirmacion("ana@ejemplo.com", ENLACE)


def test_el_error_no_filtra_la_clave_ni_el_enlace(caplog):
    manejador = lambda p: httpx.Response(401, json={"code": "unauthorized", "message": "Key not found"})
    with pytest.raises(ErrorEnvio) as error:
        _enviador(manejador).enviar_confirmacion("ana@ejemplo.com", ENLACE)
    todo = str(error.value) + caplog.text
    assert "clave-api-secreta" not in todo and "tok_abc-123" not in todo


def _capturar():
    recibidas = []

    def manejador(peticion):
        recibidas.append(json.loads(peticion.content))
        return httpx.Response(201, json={})

    return recibidas, _enviador(manejador)


def test_el_recordatorio_lleva_importe_remitente_y_grupo():
    recibidas, enviador = _capturar()
    enviador.enviar_recordatorio("beto@ejemplo.com", "ana@ejemplo.com", "Viaje", 1550, "https://x.es")
    cuerpo = recibidas[0]
    assert cuerpo["to"] == [{"email": "beto@ejemplo.com"}]
    assert "15,50 €" in cuerpo["htmlContent"] and "ana@ejemplo.com" in cuerpo["htmlContent"]
    assert "Viaje" in cuerpo["htmlContent"] and cuerpo["subject"]


def test_la_invitacion_lleva_el_grupo_y_quien_invita():
    recibidas, enviador = _capturar()
    enviador.enviar_invitacion("nuevo@ejemplo.com", "ana@ejemplo.com", "Viaje", "https://x.es")
    assert "Viaje" in recibidas[0]["htmlContent"] and "ana@ejemplo.com" in recibidas[0]["htmlContent"]
    assert recibidas[0]["to"] == [{"email": "nuevo@ejemplo.com"}]


def test_el_nombre_del_grupo_no_puede_inyectar_html_en_los_correos():
    recibidas, enviador = _capturar()
    malo = '<script>alert(1)</script>'
    enviador.enviar_recordatorio("b@e.com", "a@e.com", malo, 100, "https://x.es")
    enviador.enviar_invitacion("b@e.com", "a@e.com", malo, "https://x.es")
    for cuerpo in recibidas:
        assert "<script>" not in cuerpo["htmlContent"]
