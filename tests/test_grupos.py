from datetime import datetime, timezone

import mongomock
import pytest

from back.datos.grupos_memoria import RepositorioGruposMemoria
from back.datos.memoria import RepositorioMemoria
from back.datos.mongo import RepositorioGruposMongo, RepositorioUsuariosMongo
from back.logica.errores import (
    DatosInvalidos, GrupoNoEncontrado, NoAutorizado, UsuarioNoEncontrado, YaEsMiembro,
)
from back.externos.correo_simulado import EnviadorSimulado
from back.logica.grupos import MAX_MIEMBROS, ServicioGrupos
from back.logica.modelos import Estado
from back.logica.servicio import ServicioUsuarios


@pytest.fixture(params=["memoria", "mongo"])
def pila(request):
    if request.param == "memoria":
        usuarios = ServicioUsuarios(RepositorioMemoria(), True)
        repo = RepositorioGruposMemoria()
    else:
        base = mongomock.MongoClient()["pruebas"]
        usuarios = ServicioUsuarios(RepositorioUsuariosMongo(base), True)
        repo = RepositorioGruposMongo(base)
    servicio = ServicioGrupos(repo, usuarios, EnviadorSimulado(), "https://splitmate.ejemplo.com",
                              reloj=lambda: datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc))
    gente = {n: usuarios.registrar(f"{n}@ejemplo.com", "clave-segura-1")
             for n in ("ana", "beto", "carla", "dani")}
    return servicio, gente


def _grupo_con(pila, *nombres):
    servicio, gente = pila
    grupo = servicio.crear_grupo(gente["ana"], "Viaje")
    for n in nombres:
        servicio.anadir_miembro(gente["ana"], grupo.id, f"{n}@ejemplo.com")
    return grupo


# --- grupos -------------------------------------------------------------------
def test_crear_grupo_pone_al_creador_como_miembro(pila):
    servicio, gente = pila
    g = servicio.crear_grupo(gente["ana"], "  Piso  ")
    assert g.nombre == "Piso" and g.miembros == [gente["ana"].id]


@pytest.mark.parametrize("nombre", ["", "   ", "x" * 61])
def test_un_nombre_de_grupo_invalido_se_rechaza(pila, nombre):
    servicio, gente = pila
    with pytest.raises(DatosInvalidos):
        servicio.crear_grupo(gente["ana"], nombre)


def test_cada_persona_solo_ve_sus_grupos(pila):
    servicio, gente = pila
    servicio.crear_grupo(gente["ana"], "De Ana")
    servicio.crear_grupo(gente["beto"], "De Beto")
    assert [g.nombre for g in servicio.listar_grupos(gente["ana"])] == ["De Ana"]


def test_un_no_miembro_no_puede_ver_el_grupo_ni_saber_que_existe(pila):
    servicio, gente = pila
    g = _grupo_con(pila)
    with pytest.raises(GrupoNoEncontrado):
        servicio.detalle(gente["beto"], g.id)
    with pytest.raises(GrupoNoEncontrado):
        servicio.detalle(gente["beto"], 9999)  # mismo error que un grupo inexistente


# --- miembros -----------------------------------------------------------------
def test_anadir_miembro_por_email(pila):
    servicio, gente = pila
    g = _grupo_con(pila)
    g, resultado = servicio.anadir_miembro(gente["ana"], g.id, "  BETO@ejemplo.com ")
    assert resultado == "anadido" and gente["beto"].id in g.miembros


def test_anadir_a_una_cuenta_eliminada_falla(pila):
    servicio, gente = pila
    g = _grupo_con(pila)
    gente["carla"].estado = Estado.ELIMINADO
    servicio.usuarios.repositorio.actualizar(gente["carla"])
    with pytest.raises(UsuarioNoEncontrado):
        servicio.anadir_miembro(gente["ana"], g.id, "carla@ejemplo.com")


def test_no_se_puede_anadir_dos_veces(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto")
    with pytest.raises(YaEsMiembro):
        servicio.anadir_miembro(gente["ana"], g.id, "beto@ejemplo.com")


def test_un_no_miembro_no_puede_anadir_gente(pila):
    servicio, gente = pila
    g = _grupo_con(pila)
    with pytest.raises(GrupoNoEncontrado):
        servicio.anadir_miembro(gente["beto"], g.id, "carla@ejemplo.com")


def test_un_email_invalido_se_rechaza(pila):
    servicio, gente = pila
    g = _grupo_con(pila)
    with pytest.raises(DatosInvalidos):
        servicio.anadir_miembro(gente["ana"], g.id, "esto-no-es-un-email")


def test_hay_un_maximo_de_miembros(pila):
    servicio, gente = pila
    g = _grupo_con(pila)
    for i in range(MAX_MIEMBROS - 1):
        u = servicio.usuarios.registrar(f"extra{i}@ejemplo.com", "clave-segura-1")
        servicio.anadir_miembro(gente["ana"], g.id, u.email)
    with pytest.raises(DatosInvalidos):
        servicio.anadir_miembro(gente["ana"], g.id, "beto@ejemplo.com")


# --- gastos -------------------------------------------------------------------
def test_registrar_un_gasto_y_ver_los_saldos(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto", "carla")
    a, b, c = (gente[n].id for n in ("ana", "beto", "carla"))
    servicio.registrar_gasto(gente["ana"], g.id, "Cena", 3000, a, [a, b, c])
    d = servicio.detalle(gente["beto"], g.id)
    assert d.saldos == {a: 2000, b: -1000, c: -1000}
    assert sorted(d.transferencias) == [(b, a, 1000), (c, a, 1000)]


@pytest.mark.parametrize("campo,valor", [
    ("concepto", ""), ("concepto", "x" * 81), ("importe", 0), ("importe", -5),
    ("importe", 100_000_001),
])
def test_un_gasto_con_datos_invalidos_se_rechaza(pila, campo, valor):
    servicio, gente = pila
    g = _grupo_con(pila)
    a = gente["ana"].id
    datos = {"concepto": "Cena", "importe": 1000}
    datos[campo] = valor
    with pytest.raises(DatosInvalidos):
        servicio.registrar_gasto(gente["ana"], g.id, datos["concepto"], datos["importe"], a, [a])


def test_el_pagador_y_los_participantes_deben_ser_miembros(pila):
    servicio, gente = pila
    g = _grupo_con(pila)
    a, intruso = gente["ana"].id, gente["dani"].id
    with pytest.raises(DatosInvalidos):
        servicio.registrar_gasto(gente["ana"], g.id, "Cena", 1000, intruso, [a])
    with pytest.raises(DatosInvalidos):
        servicio.registrar_gasto(gente["ana"], g.id, "Cena", 1000, a, [a, intruso])


def test_participantes_vacios_o_repetidos_se_rechazan(pila):
    servicio, gente = pila
    g = _grupo_con(pila)
    a = gente["ana"].id
    with pytest.raises(DatosInvalidos):
        servicio.registrar_gasto(gente["ana"], g.id, "Cena", 1000, a, [])
    with pytest.raises(DatosInvalidos):
        servicio.registrar_gasto(gente["ana"], g.id, "Cena", 1000, a, [a, a])


def test_un_no_miembro_no_puede_registrar_gastos(pila):
    servicio, gente = pila
    g = _grupo_con(pila)
    with pytest.raises(GrupoNoEncontrado):
        servicio.registrar_gasto(gente["dani"], g.id, "Cena", 1000, gente["dani"].id, [gente["dani"].id])


def test_solo_quien_registro_el_gasto_o_el_creador_lo_borra(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto", "carla")
    a, b, c = (gente[n].id for n in ("ana", "beto", "carla"))
    gasto = servicio.registrar_gasto(gente["beto"], g.id, "Taxi", 1000, b, [a, b, c])
    with pytest.raises(NoAutorizado):
        servicio.eliminar_gasto(gente["carla"], g.id, gasto.id)
    servicio.eliminar_gasto(gente["ana"], g.id, gasto.id)  # el creador del grupo puede
    assert servicio.detalle(gente["ana"], g.id).gastos == []


def test_no_se_puede_borrar_un_gasto_de_otro_grupo(pila):
    servicio, gente = pila
    g1 = _grupo_con(pila)
    g2 = servicio.crear_grupo(gente["ana"], "Otro")
    a = gente["ana"].id
    gasto = servicio.registrar_gasto(gente["ana"], g1.id, "Cena", 1000, a, [a])
    with pytest.raises(DatosInvalidos):
        servicio.eliminar_gasto(gente["ana"], g2.id, gasto.id)


# --- pagos ----------------------------------------------------------------------
def test_un_pago_salda_la_deuda(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    servicio.registrar_gasto(gente["ana"], g.id, "Cena", 2000, a, [a, b])
    servicio.registrar_liquidacion(gente["beto"], g.id, b, a, 1000)
    d = servicio.detalle(gente["ana"], g.id)
    assert d.saldos == {a: 0, b: 0} and d.transferencias == []
    assert len(d.liquidaciones) == 1


def test_un_tercero_no_puede_registrar_un_pago_ajeno(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto", "carla")
    a, b, c = (gente[n].id for n in ("ana", "beto", "carla"))
    with pytest.raises(NoAutorizado):
        servicio.registrar_liquidacion(gente["carla"], g.id, a, b, 500)


def test_se_puede_pagar_la_deuda_en_varias_veces(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    servicio.registrar_gasto(gente["ana"], g.id, "Cena", 2000, a, [a, b])
    servicio.registrar_liquidacion(gente["beto"], g.id, b, a, 400)
    servicio.registrar_liquidacion(gente["ana"], g.id, b, a, 600)  # también puede apuntarlo quien cobra
    d = servicio.detalle(gente["ana"], g.id)
    assert d.saldos == {a: 0, b: 0} and len(d.liquidaciones) == 2


def test_un_pago_mayor_que_la_deuda_se_rechaza_e_indica_el_maximo(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    servicio.registrar_gasto(gente["ana"], g.id, "Cena", 2000, a, [a, b])
    with pytest.raises(DatosInvalidos, match="10,00 €"):
        servicio.registrar_liquidacion(gente["beto"], g.id, b, a, 1001)  # un céntimo de más
    d = servicio.detalle(gente["ana"], g.id)
    assert d.saldos == {a: 1000, b: -1000} and d.liquidaciones == []


def test_tras_un_pago_parcial_el_maximo_es_lo_que_queda(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    servicio.registrar_gasto(gente["ana"], g.id, "Cena", 2000, a, [a, b])
    servicio.registrar_liquidacion(gente["beto"], g.id, b, a, 750)
    with pytest.raises(DatosInvalidos, match="2,50 €"):
        servicio.registrar_liquidacion(gente["beto"], g.id, b, a, 251)
    servicio.registrar_liquidacion(gente["beto"], g.id, b, a, 250)
    assert servicio.detalle(gente["ana"], g.id).saldos == {a: 0, b: 0}


def test_no_se_puede_pagar_si_no_hay_deuda(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto")
    a, b = gente["ana"].id, gente["beto"].id
    with pytest.raises(DatosInvalidos, match="no debe nada"):
        servicio.registrar_liquidacion(gente["beto"], g.id, b, a, 100)
    servicio.registrar_gasto(gente["ana"], g.id, "Cena", 2000, a, [a, b])
    # Al revés tampoco: Ana es la acreedora, pagar a Beto crearía una deuda falsa
    with pytest.raises(DatosInvalidos, match="no debe nada"):
        servicio.registrar_liquidacion(gente["ana"], g.id, a, b, 100)


def test_no_se_puede_pagar_a_quien_no_le_deben(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto", "carla")
    a, b, c = (gente[n].id for n in ("ana", "beto", "carla"))
    servicio.registrar_gasto(gente["ana"], g.id, "Cena", 3000, a, [a, b, c])
    # Beto debe 10 € pero a Carla no le deben nada: el pago descuadraría a Carla
    with pytest.raises(DatosInvalidos, match="no le deben nada"):
        servicio.registrar_liquidacion(gente["beto"], g.id, b, c, 500)


def test_el_maximo_es_lo_menor_entre_lo_que_se_debe_y_lo_que_le_deben(pila):
    servicio, gente = pila
    g = _grupo_con(pila, "beto", "carla")
    a, b, c = (gente[n].id for n in ("ana", "beto", "carla"))
    # Ana y Carla pagan, Beto no: Beto debe 25 €, a Ana le deben 15 € y a Carla 10 €
    servicio.registrar_gasto(gente["ana"], g.id, "Hotel", 3000, a, [a, b])
    servicio.registrar_gasto(gente["carla"], g.id, "Taxi", 2000, c, [b, c])
    assert servicio.detalle(gente["ana"], g.id).saldos == {a: 1500, b: -2500, c: 1000}
    with pytest.raises(DatosInvalidos, match="10,00 €"):
        servicio.registrar_liquidacion(gente["beto"], g.id, b, c, 1500)
    # Se puede pagar a cualquier acreedor, no solo al de la transferencia sugerida
    servicio.registrar_liquidacion(gente["beto"], g.id, b, c, 1000)
    servicio.registrar_liquidacion(gente["beto"], g.id, b, a, 1500)
    assert servicio.detalle(gente["ana"], g.id).saldos == {a: 0, b: 0, c: 0}


@pytest.mark.parametrize("de,a,importe", [("ana", "ana", 100), ("ana", "beto", 0), ("ana", "dani", 100)])
def test_pagos_invalidos_se_rechazan(pila, de, a, importe):
    servicio, gente = pila
    g = _grupo_con(pila, "beto")
    with pytest.raises(DatosInvalidos):
        servicio.registrar_liquidacion(gente["ana"], g.id, gente[de].id, gente[a].id, importe)
