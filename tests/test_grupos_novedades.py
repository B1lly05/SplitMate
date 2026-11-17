"""Pesos por persona, línea de actividad, recordatorios e invitaciones."""
from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from back.datos.grupos_memoria import RepositorioGruposMemoria
from back.datos.memoria import RepositorioMemoria
from back.datos.mongo import RepositorioGruposMongo, RepositorioUsuariosMongo
from back.externos.correo_simulado import EnviadorSimulado
from back.logica.errores import CorreoNoEnviado, DatosInvalidos, GrupoNoEncontrado
from back.logica.grupos import LIMITE_ACTIVIDAD, MAX_INVITACIONES_PENDIENTES, ServicioGrupos
from back.logica.modelos import Estado
from back.logica.servicio import ServicioUsuarios

BASE = "https://splitmate.ejemplo.com"


class Reloj:
    def __init__(self):
        self.ahora = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.ahora

    def avanzar(self, **t):
        self.ahora += timedelta(**t)


@pytest.fixture(params=["memoria", "mongo"])
def pila(request):
    reloj, enviador = Reloj(), EnviadorSimulado()
    if request.param == "memoria":
        usuarios = ServicioUsuarios(RepositorioMemoria(), True)
        repo = RepositorioGruposMemoria()
    else:
        base = mongomock.MongoClient()["pruebas"]
        usuarios = ServicioUsuarios(RepositorioUsuariosMongo(base), True)
        repo = RepositorioGruposMongo(base)
    servicio = ServicioGrupos(repo, usuarios, enviador, BASE, reloj=reloj)
    gente = {n: usuarios.registrar(f"{n}@ejemplo.com", "clave-segura-1")
             for n in ("ana", "beto", "carla")}
    grupo = servicio.crear_grupo(gente["ana"], "Viaje")
    return servicio, gente, grupo, enviador, reloj


def _con_miembros(pila, *nombres):
    servicio, gente, grupo, *_ = pila
    for n in nombres:
        servicio.anadir_miembro(gente["ana"], grupo.id, f"{n}@ejemplo.com")


# =============================== pesos ==========================================
def test_un_gasto_con_pesos_reparte_en_proporcion(pila):
    servicio, gente, grupo, *_ = pila
    _con_miembros(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    servicio.registrar_gasto(gente["ana"], grupo.id, "Alquiler", 3000, a, [a, b], {a: 1, b: 2})
    assert servicio.detalle(gente["ana"], grupo.id).saldos == {a: 2000, b: -2000}


def test_los_pesos_se_conservan_tal_cual_al_guardar_y_leer(pila):
    servicio, gente, grupo, *_ = pila
    _con_miembros(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    servicio.registrar_gasto(gente["ana"], grupo.id, "Cena", 900, a, [a, b], {a: 1, b: 3})
    assert servicio.detalle(gente["ana"], grupo.id).gastos[0].pesos == {b: 3}  # el 1 no se guarda


@pytest.mark.parametrize("peso", [0, -1, 11, 100])
def test_un_peso_fuera_de_rango_se_rechaza(pila, peso):
    servicio, gente, grupo, *_ = pila
    a = gente["ana"].id
    with pytest.raises(DatosInvalidos):
        servicio.registrar_gasto(gente["ana"], grupo.id, "Cena", 900, a, [a], {a: peso})


def test_los_pesos_solo_valen_para_quienes_participan(pila):
    servicio, gente, grupo, *_ = pila
    _con_miembros(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    with pytest.raises(DatosInvalidos):
        servicio.registrar_gasto(gente["ana"], grupo.id, "Cena", 900, a, [a], {b: 2})


# ============================ actividad ==========================================
def test_la_actividad_registra_cada_accion_y_la_mas_reciente_va_primero(pila):
    servicio, gente, grupo, *_ = pila
    _con_miembros(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    gasto = servicio.registrar_gasto(gente["ana"], grupo.id, "Cena", 2000, a, [a, b])
    servicio.registrar_liquidacion(gente["beto"], grupo.id, b, a, 1000)
    servicio.eliminar_gasto(gente["ana"], grupo.id, gasto.id)
    tipos = [e.tipo for e in servicio.detalle(gente["ana"], grupo.id).actividad]
    assert tipos == ["gasto_eliminado", "pago_registrado", "gasto_creado",
                     "miembro_anadido", "grupo_creado"]


def test_la_actividad_guarda_quien_lo_hizo_y_los_datos(pila):
    servicio, gente, grupo, *_ = pila
    a = gente["ana"].id
    servicio.registrar_gasto(gente["ana"], grupo.id, "Cena", 2000, a, [a])
    ultima = servicio.detalle(gente["ana"], grupo.id).actividad[0]
    assert ultima.usuario_id == a and ultima.datos == {"concepto": "Cena", "importe": 2000}


def test_la_actividad_esta_limitada(pila):
    servicio, gente, grupo, *_ = pila
    a = gente["ana"].id
    for i in range(LIMITE_ACTIVIDAD + 5):
        servicio.registrar_gasto(gente["ana"], grupo.id, f"Gasto {i}", 100, a, [a])
    assert len(servicio.detalle(gente["ana"], grupo.id).actividad) == LIMITE_ACTIVIDAD


def test_la_actividad_es_privada_del_grupo(pila):
    servicio, gente, grupo, *_ = pila
    with pytest.raises(GrupoNoEncontrado):
        servicio.detalle(gente["carla"], grupo.id)


# ============================ recordatorios ======================================
def _deuda(pila):
    """Ana pagó 30 € entre ella y Beto: Beto le debe 15 €."""
    servicio, gente, grupo, *_ = pila
    _con_miembros(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    servicio.registrar_gasto(gente["ana"], grupo.id, "Cena", 3000, a, [a, b])
    return servicio, gente, grupo


def test_recordar_envia_un_correo_al_deudor_con_el_importe(pila):
    servicio, gente, grupo = _deuda(pila)
    enviador = pila[3]
    assert servicio.recordar(gente["ana"], grupo.id, gente["beto"].id) == 1500
    assert enviador.recordatorios == [("beto@ejemplo.com", "ana@ejemplo.com", "Viaje", 1500)]
    assert servicio.detalle(gente["ana"], grupo.id).actividad[0].tipo == "recordatorio_enviado"


def test_solo_puede_recordar_quien_es_acreedor(pila):
    servicio, gente, grupo = _deuda(pila)
    with pytest.raises(DatosInvalidos):  # Beto no le debe nada a Beto ni Ana le debe a Beto
        servicio.recordar(gente["beto"], grupo.id, gente["ana"].id)
    assert pila[3].recordatorios == []


def test_no_se_puede_recordar_una_deuda_ya_saldada(pila):
    servicio, gente, grupo = _deuda(pila)
    a, b = gente["ana"].id, gente["beto"].id
    servicio.registrar_liquidacion(gente["beto"], grupo.id, b, a, 1500)
    with pytest.raises(DatosInvalidos):
        servicio.recordar(gente["ana"], grupo.id, b)


def test_un_solo_recordatorio_al_dia_por_persona(pila):
    servicio, gente, grupo = _deuda(pila)
    reloj = pila[4]
    servicio.recordar(gente["ana"], grupo.id, gente["beto"].id)
    reloj.avanzar(hours=3)
    with pytest.raises(DatosInvalidos):
        servicio.recordar(gente["ana"], grupo.id, gente["beto"].id)
    reloj.avanzar(hours=22)
    servicio.recordar(gente["ana"], grupo.id, gente["beto"].id)
    assert len(pila[3].recordatorios) == 2


def test_si_falla_el_envio_se_avisa_y_no_queda_rastro(pila):
    servicio, gente, grupo = _deuda(pila)
    pila[3].fallar = True
    with pytest.raises(CorreoNoEnviado):
        servicio.recordar(gente["ana"], grupo.id, gente["beto"].id)
    tipos = [e.tipo for e in servicio.detalle(gente["ana"], grupo.id).actividad]
    assert "recordatorio_enviado" not in tipos


def test_el_deudor_debe_ser_del_grupo_y_el_que_pide_miembro(pila):
    servicio, gente, grupo = _deuda(pila)
    with pytest.raises(DatosInvalidos):
        servicio.recordar(gente["ana"], grupo.id, gente["carla"].id)
    with pytest.raises(GrupoNoEncontrado):
        servicio.recordar(gente["carla"], grupo.id, gente["beto"].id)


# ============================= invitaciones ======================================
def test_invitar_a_alguien_sin_cuenta_envia_un_correo(pila):
    servicio, gente, grupo, enviador, _ = pila
    _, resultado = servicio.anadir_miembro(gente["ana"], grupo.id, "  Nuevo@Ejemplo.com ")
    assert resultado == "invitado"
    assert enviador.invitaciones == [("nuevo@ejemplo.com", "ana@ejemplo.com", "Viaje")]
    d = servicio.detalle(gente["ana"], grupo.id)
    assert [i.email for i in d.invitaciones] == ["nuevo@ejemplo.com"]
    assert d.actividad[0].tipo == "invitacion_enviada"
    assert len(d.miembros) == 1  # todavía no es miembro


def test_no_se_puede_invitar_dos_veces_a_la_misma_persona(pila):
    servicio, gente, grupo, enviador, _ = pila
    servicio.anadir_miembro(gente["ana"], grupo.id, "nuevo@ejemplo.com")
    with pytest.raises(DatosInvalidos):
        servicio.anadir_miembro(gente["ana"], grupo.id, "nuevo@ejemplo.com")
    assert len(enviador.invitaciones) == 1


def test_hay_un_maximo_de_invitaciones_pendientes(pila):
    servicio, gente, grupo, *_ = pila
    for i in range(MAX_INVITACIONES_PENDIENTES):
        servicio.anadir_miembro(gente["ana"], grupo.id, f"x{i}@ejemplo.com")
    with pytest.raises(DatosInvalidos):
        servicio.anadir_miembro(gente["ana"], grupo.id, "uno-mas@ejemplo.com")


def test_si_falla_el_correo_no_se_crea_la_invitacion(pila):
    servicio, gente, grupo, enviador, _ = pila
    enviador.fallar = True
    with pytest.raises(CorreoNoEnviado):
        servicio.anadir_miembro(gente["ana"], grupo.id, "nuevo@ejemplo.com")
    assert servicio.detalle(gente["ana"], grupo.id).invitaciones == []


def test_quien_se_registra_con_el_email_invitado_entra_en_el_grupo(pila):
    servicio, gente, grupo, *_ = pila
    servicio.anadir_miembro(gente["ana"], grupo.id, "nuevo@ejemplo.com")
    nuevo = servicio.usuarios.registrar("nuevo@ejemplo.com", "clave-segura-1")
    assert [g.id for g in servicio.listar_grupos(nuevo)] == [grupo.id]
    d = servicio.detalle(gente["ana"], grupo.id)
    assert nuevo.id in d.grupo.miembros and d.invitaciones == []  # la invitación se consume
    assert d.actividad[0].tipo == "invitacion_aceptada" and d.actividad[0].usuario_id == nuevo.id


def test_una_invitacion_no_vale_para_otro_email(pila):
    servicio, gente, grupo, *_ = pila
    servicio.anadir_miembro(gente["ana"], grupo.id, "nuevo@ejemplo.com")
    assert servicio.listar_grupos(gente["carla"]) == []


def test_una_invitacion_caducada_no_se_acepta(pila):
    servicio, gente, grupo, _, reloj = pila
    servicio.anadir_miembro(gente["ana"], grupo.id, "nuevo@ejemplo.com")
    reloj.avanzar(days=15)
    nuevo = servicio.usuarios.registrar("nuevo@ejemplo.com", "clave-segura-1")
    assert servicio.listar_grupos(nuevo) == []


def test_una_cuenta_sin_activar_recibe_invitacion_y_entra_al_activarse(pila):
    servicio, gente, grupo, enviador, _ = pila
    pendiente = ServicioUsuarios(servicio.usuarios.repositorio, False).registrar(
        "pendiente@ejemplo.com", "clave-segura-1")
    assert pendiente.estado == Estado.PENDIENTE
    _, resultado = servicio.anadir_miembro(gente["ana"], grupo.id, "pendiente@ejemplo.com")
    assert resultado == "invitado"
    pendiente.estado = Estado.ACTIVO  # confirma su correo
    servicio.usuarios.repositorio.actualizar(pendiente)
    assert [g.id for g in servicio.listar_grupos(pendiente)] == [grupo.id]
