import hashlib
import logging
from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from back.datos.memoria import RepositorioMemoria
from back.datos.mongo import RepositorioTokensMongo, RepositorioUsuariosMongo
from back.datos.tokens_memoria import RepositorioTokensMemoria
from back.externos.correo_simulado import EnviadorSimulado
from back.logica.confirmacion import ServicioConfirmacion
from back.logica.errores import TokenInvalido
from back.logica.modelos import Estado, Rol
from back.logica.servicio import ServicioUsuarios

BASE = "https://splitmate.ejemplo.com"
CLAVE = "clave-segura-1"


class Reloj:
    def __init__(self):
        self.ahora = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.ahora

    def avanzar(self, **tiempo):
        self.ahora += timedelta(**tiempo)


@pytest.fixture(params=["memoria", "mongo"])
def pila(request):
    reloj = Reloj()
    enviador = EnviadorSimulado()
    if request.param == "memoria":
        usuarios = ServicioUsuarios(RepositorioMemoria())
        tokens = RepositorioTokensMemoria()
    else:
        base = mongomock.MongoClient()["pruebas"]
        usuarios = ServicioUsuarios(RepositorioUsuariosMongo(base))
        tokens = RepositorioTokensMongo(base)
    servicio = ServicioConfirmacion(usuarios, tokens, enviador, BASE, reloj=reloj)
    return servicio, usuarios, enviador, reloj, tokens


def _token_del_enlace(enlace):
    return enlace.split("?confirmar=")[1]


def _registrar(pila, email="ana@ejemplo.com"):
    servicio, usuarios, enviador, _, _ = pila
    u = usuarios.registrar(email, CLAVE)
    servicio.enviar_si_pendiente(u)
    return u, _token_del_enlace(enviador.enviados[-1][1])


def test_el_correo_lleva_un_enlace_con_token_y_va_al_destinatario(pila):
    _, usuarios, enviador, _, _ = pila
    _registrar(pila)
    destinatario, enlace = enviador.enviados[0]
    assert destinatario == "ana@ejemplo.com"
    assert enlace.startswith(BASE + "/?confirmar=") and len(_token_del_enlace(enlace)) >= 30


def test_en_la_base_de_datos_solo_se_guarda_el_hash_del_token(pila):
    _, _, _, _, tokens = pila
    u, token = _registrar(pila)
    guardado = tokens.obtener_de_usuario(u.id)
    assert guardado.clave != token
    assert guardado.clave == hashlib.sha256(token.encode()).hexdigest()


def test_confirmar_activa_la_cuenta_pendiente(pila):
    servicio, usuarios, _, _, _ = pila
    u, token = _registrar(pila)
    assert u.estado == Estado.PENDIENTE
    servicio.confirmar(token)
    assert usuarios.repositorio.obtener_por_id(u.id).estado == Estado.ACTIVO


def test_el_token_solo_vale_una_vez(pila):
    servicio, *_ = pila
    _, token = _registrar(pila)
    servicio.confirmar(token)
    with pytest.raises(TokenInvalido):
        servicio.confirmar(token)


def test_un_token_caducado_se_rechaza_y_no_activa_la_cuenta(pila):
    servicio, usuarios, _, reloj, _ = pila
    u, token = _registrar(pila)
    reloj.avanzar(hours=25)
    with pytest.raises(TokenInvalido):
        servicio.confirmar(token)
    assert usuarios.repositorio.obtener_por_id(u.id).estado == Estado.PENDIENTE


@pytest.mark.parametrize("token", ["", "inventado", "a" * 43])
def test_un_token_desconocido_o_vacio_se_rechaza(pila, token):
    servicio, *_ = pila
    with pytest.raises(TokenInvalido):
        servicio.confirmar(token)


def test_una_cuenta_eliminada_no_se_puede_confirmar(pila):
    servicio, usuarios, _, _, _ = pila
    u, token = _registrar(pila)
    u.estado = Estado.ELIMINADO
    usuarios.repositorio.actualizar(u)
    with pytest.raises(TokenInvalido):
        servicio.confirmar(token)
    assert usuarios.repositorio.obtener_por_id(u.id).estado == Estado.ELIMINADO


def test_un_envio_nuevo_anula_el_enlace_anterior(pila):
    servicio, usuarios, enviador, reloj, _ = pila
    u, primero = _registrar(pila)
    reloj.avanzar(minutes=5)
    servicio.enviar_si_pendiente(u)
    segundo = _token_del_enlace(enviador.enviados[-1][1])
    with pytest.raises(TokenInvalido):
        servicio.confirmar(primero)
    assert servicio.confirmar(segundo).estado == Estado.ACTIVO


def test_no_se_envia_correo_a_una_cuenta_ya_activa(pila):
    servicio, usuarios, enviador, _, _ = pila
    u = usuarios.registrar("ana@ejemplo.com", CLAVE)
    u.estado = Estado.ACTIVO
    usuarios.repositorio.actualizar(u)
    assert servicio.enviar_si_pendiente(u) is False
    assert enviador.enviados == []


def test_si_el_envio_falla_no_se_rompe_y_no_queda_token(pila):
    servicio, usuarios, enviador, _, tokens = pila
    enviador.fallar = True
    u = usuarios.registrar("ana@ejemplo.com", CLAVE)
    assert servicio.enviar_si_pendiente(u) is False
    assert tokens.obtener_de_usuario(u.id) is None


def test_reenviar_a_una_cuenta_pendiente_envia_otro_correo(pila):
    servicio, _, enviador, reloj, _ = pila
    _registrar(pila)
    reloj.avanzar(minutes=2)
    servicio.reenviar("  ANA@ejemplo.com ")
    assert len(enviador.enviados) == 2


def test_reenviar_respeta_la_espera_minima(pila):
    servicio, _, enviador, reloj, _ = pila
    _registrar(pila)
    reloj.avanzar(seconds=10)
    servicio.reenviar("ana@ejemplo.com")
    assert len(enviador.enviados) == 1
    reloj.avanzar(seconds=60)
    servicio.reenviar("ana@ejemplo.com")
    assert len(enviador.enviados) == 2


def test_reenviar_a_un_correo_desconocido_no_falla_ni_envia(pila):
    servicio, _, enviador, _, _ = pila
    servicio.reenviar("nadie@ejemplo.com")
    assert enviador.enviados == []


def test_reenviar_no_escribe_a_cuentas_activas(pila):
    servicio, usuarios, enviador, _, _ = pila
    u = usuarios.registrar("ana@ejemplo.com", CLAVE)
    u.estado = Estado.ACTIVO
    usuarios.repositorio.actualizar(u)
    servicio.reenviar("ana@ejemplo.com")
    assert enviador.enviados == []


def test_reenviar_ignora_cuentas_sin_contrasena_local(pila):
    servicio, usuarios, enviador, _, _ = pila
    usuarios.repositorio.crear("ana@ejemplo.com", Rol.USUARIO, Estado.PENDIENTE, None)
    servicio.reenviar("ana@ejemplo.com")
    assert enviador.enviados == []


def test_los_logs_no_contienen_el_token_ni_el_enlace(pila, caplog):
    caplog.set_level(logging.DEBUG, logger="splitmate")
    servicio, *_ = pila
    _, token = _registrar(pila)
    servicio.confirmar(token)
    with pytest.raises(TokenInvalido):
        servicio.confirmar(token)
    assert token not in caplog.text
    assert "confirmar=" not in caplog.text
