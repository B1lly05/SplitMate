import random

import pytest

from back.logica.modelos import Gasto, Liquidacion
from back.logica.saldos import calcular_saldos, repartir, simplificar


def _gasto(id, importe, pagador, participantes):
    return Gasto(id, 1, "x", importe, pagador, participantes, pagador, "2026-11-16")


def test_repartir_a_partes_iguales():
    assert repartir(900, [1, 2, 3]) == {1: 300, 2: 300, 3: 300}


def test_repartir_nunca_pierde_ni_inventa_centimos():
    for importe in (1, 2, 100, 1001, 999_999):
        for n in (1, 2, 3, 7):
            assert sum(repartir(importe, list(range(n)), 5).values()) == importe


def test_los_centimos_sobrantes_rotan_con_la_semilla():
    quien_recibe = {max(repartir(100, [1, 2, 3], s), key=repartir(100, [1, 2, 3], s).get)
                    for s in range(3)}
    assert quien_recibe == {1, 2, 3}  # no le toca siempre a la misma persona


def test_saldos_de_un_gasto_sencillo():
    saldos = calcular_saldos([_gasto(1, 3000, 1, [1, 2, 3])], [])
    assert saldos == {1: 2000, 2: -1000, 3: -1000}


def test_quien_paga_y_no_participa_solo_cobra():
    saldos = calcular_saldos([_gasto(1, 1000, 1, [2, 3])], [])
    assert saldos == {1: 1000, 2: -500, 3: -500}


def test_un_pago_reduce_la_deuda():
    gastos = [_gasto(1, 3000, 1, [1, 2, 3])]
    saldos = calcular_saldos(gastos, [Liquidacion(1, 1, 2, 1, 1000, "2026-11-16")])
    assert saldos[2] == 0 and saldos[1] == 1000 and saldos[3] == -1000


def test_sin_gastos_no_hay_saldos():
    assert calcular_saldos([], []) == {}
    assert simplificar({}) == []


def test_simplificar_deja_todo_a_cero():
    pagos = simplificar({1: 2000, 2: -1000, 3: -1000})
    assert sorted(pagos) == [(2, 1, 1000), (3, 1, 1000)]


def test_simplificar_usa_pocas_transferencias():
    # 4 personas: dos acreedoras y dos deudoras → como mucho 3 pagos (n-1)
    pagos = simplificar({1: 500, 2: 300, 3: -600, 4: -200})
    assert len(pagos) <= 3


@pytest.mark.parametrize("semilla", range(30))
def test_propiedad_los_saldos_suman_cero_y_las_transferencias_los_saldan(semilla):
    azar = random.Random(semilla)
    personas = list(range(1, azar.randint(2, 8)))
    gastos = []
    for i in range(1, azar.randint(1, 15)):
        participantes = azar.sample(personas, azar.randint(1, len(personas)))
        gastos.append(_gasto(i, azar.randint(1, 50_000), azar.choice(personas), participantes))
    saldos = calcular_saldos(gastos, [])
    assert sum(saldos.values()) == 0
    for deudor, acreedor, importe in simplificar(saldos):
        assert importe > 0 and deudor != acreedor
        saldos[deudor] += importe
        saldos[acreedor] -= importe
    assert all(s == 0 for s in saldos.values())


# --- partes por persona -----------------------------------------------------------
def test_repartir_con_pesos_en_proporcion():
    assert repartir(900, [1, 2], pesos={1: 2, 2: 1}) == {1: 600, 2: 300}


def test_el_centimo_sobrante_va_a_quien_tiene_mayor_resto():
    # 100 céntimos en proporción 2:1 → 66,67 y 33,33 → 67 y 33
    assert repartir(100, [1, 2], pesos={1: 2, 2: 1}) == {1: 67, 2: 33}


def test_quien_no_tiene_peso_cuenta_como_uno():
    assert repartir(300, [1, 2, 3], pesos={1: 2}) == {1: 150, 2: 75, 3: 75}


def test_sin_pesos_el_reparto_es_igual_que_antes():
    assert repartir(100, [1, 2, 3], 1, {}) == repartir(100, [1, 2, 3], 1)


@pytest.mark.parametrize("semilla", range(40))
def test_propiedad_con_pesos_la_suma_siempre_es_exacta(semilla):
    azar = random.Random(semilla)
    ids = list(range(1, azar.randint(2, 7)))
    pesos = {uid: azar.randint(1, 10) for uid in ids}
    importe = azar.randint(1, 1_000_000)
    reparto = repartir(importe, ids, azar.randint(0, 50), pesos)
    assert sum(reparto.values()) == importe and all(v >= 0 for v in reparto.values())


def test_los_saldos_usan_los_pesos_del_gasto():
    gasto = Gasto(1, 1, "Alquiler", 3000, 1, [1, 2], 1, "2026-11-16", {2: 2})
    assert calcular_saldos([gasto], []) == {1: 2000, 2: -2000}
