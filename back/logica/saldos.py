"""Cálculo de quién debe a quién. Funciones puras (sin base de datos ni HTTP) para
poder probarlas a fondo. Todos los importes son enteros en céntimos."""
from back.logica.modelos import Gasto, Liquidacion


def repartir(importe: int, participantes: list[int], semilla: int = 0) -> dict[int, int]:
    """Reparte un importe a partes iguales sin perder ni inventar ningún céntimo.
    Si no es divisible, los céntimos sobrantes se dan de uno en uno; la semilla
    (el id del gasto) rota quién los recibe para que no sea siempre la misma persona."""
    ids = sorted(participantes)
    base, resto = divmod(importe, len(ids))
    inicio = semilla % len(ids)
    reparto = {uid: base for uid in ids}
    for i in range(resto):
        reparto[ids[(inicio + i) % len(ids)]] += 1
    return reparto


def calcular_saldos(gastos: list[Gasto], liquidaciones: list[Liquidacion]) -> dict[int, int]:
    """Saldo neto por persona: positivo = le deben dinero, negativo = debe dinero."""
    saldos: dict[int, int] = {}

    def sumar(uid: int, cantidad: int) -> None:
        saldos[uid] = saldos.get(uid, 0) + cantidad

    for gasto in gastos:
        sumar(gasto.pagador_id, gasto.importe)
        for uid, parte in repartir(gasto.importe, gasto.participantes, gasto.id).items():
            sumar(uid, -parte)
    for pago in liquidaciones:
        sumar(pago.de_id, pago.importe)   # quien paga reduce su deuda
        sumar(pago.a_id, -pago.importe)   # quien cobra reduce lo que le deben
    return saldos


def simplificar(saldos: dict[int, int]) -> list[tuple[int, int, int]]:
    """Transferencias (deudor, acreedor, importe) que dejan todos los saldos a cero
    con pocos pagos: el que más debe paga al que más le deben, y se repite."""
    deudores = sorted(((-s, uid) for uid, s in saldos.items() if s < 0), key=lambda x: (-x[0], x[1]))
    acreedores = sorted(((s, uid) for uid, s in saldos.items() if s > 0), key=lambda x: (-x[0], x[1]))
    deudores = [list(x) for x in deudores]
    acreedores = [list(x) for x in acreedores]
    pagos: list[tuple[int, int, int]] = []
    i = j = 0
    while i < len(deudores) and j < len(acreedores):
        pago = min(deudores[i][0], acreedores[j][0])
        pagos.append((deudores[i][1], acreedores[j][1], pago))
        deudores[i][0] -= pago
        acreedores[j][0] -= pago
        if deudores[i][0] == 0:
            i += 1
        if acreedores[j][0] == 0:
            j += 1
    return pagos
