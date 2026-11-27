import pytest
from fastapi.testclient import TestClient

from back.api.dependencias import get_auth, get_grupos, get_servicio
from back.datos.grupos_memoria import RepositorioGruposMemoria
from back.datos.memoria import RepositorioMemoria
from back.datos.sesiones_memoria import RepositorioSesionesMemoria
from back.externos.correo_simulado import EnviadorSimulado
from back.logica.auth import ServicioAuth
from back.logica.grupos import ServicioGrupos
from back.logica.servicio import ServicioUsuarios
from back.main import app

CLAVE = "clave-segura-1"


@pytest.fixture
def entorno():
    usuarios = ServicioUsuarios(RepositorioMemoria(), True)  # cuentas activas al registrarse
    auth = ServicioAuth(usuarios, RepositorioSesionesMemoria())
    grupos = ServicioGrupos(RepositorioGruposMemoria(), usuarios, EnviadorSimulado(),
                            "https://splitmate.ejemplo.com")
    app.dependency_overrides[get_servicio] = lambda: usuarios
    app.dependency_overrides[get_auth] = lambda: auth
    app.dependency_overrides[get_grupos] = lambda: grupos
    yield usuarios
    app.dependency_overrides.clear()


def _persona(usuarios, email):
    """Un navegador distinto por persona (cada TestClient tiene su propia cookie)."""
    usuario = usuarios.registrar(email, CLAVE)
    cliente = TestClient(app)
    assert cliente.post("/auth/login", json={"email": email, "password": CLAVE}).status_code == 200
    return cliente, usuario.id


def test_todas_las_rutas_exigen_sesion(entorno):
    anonimo = TestClient(app)
    assert anonimo.get("/grupos").status_code == 401
    assert anonimo.post("/grupos", json={"nombre": "x"}).status_code == 401
    assert anonimo.get("/grupos/1").status_code == 401
    assert anonimo.post("/grupos/1/gastos", json={}).status_code in (401, 422)
    assert anonimo.delete("/grupos/1/gastos/1").status_code == 401


def test_recorrido_completo_de_un_grupo(entorno):
    ana, a = _persona(entorno, "ana@ejemplo.com")
    beto, b = _persona(entorno, "beto@ejemplo.com")

    r = ana.post("/grupos", json={"nombre": "Viaje"})
    assert r.status_code == 201
    gid = r.json()["id"]
    assert ana.post(f"/grupos/{gid}/miembros", json={"email": "beto@ejemplo.com"}).status_code == 201

    r = ana.post(f"/grupos/{gid}/gastos",
                 json={"concepto": "Cena", "importe": 2000, "pagador_id": a, "participantes": [a, b]})
    assert r.status_code == 201

    # Beto, desde su propio navegador, ve el grupo y lo que debe
    d = beto.get(f"/grupos/{gid}").json()
    assert d["nombre"] == "Viaje" and len(d["miembros"]) == 2 and len(d["gastos"]) == 1
    assert d["transferencias"] == [{"de_id": b, "a_id": a, "importe": 1000}]
    assert {s["usuario_id"]: s["saldo"] for s in d["saldos"]} == {a: 1000, b: -1000}

    # Beto paga y queda todo saldado
    assert beto.post(f"/grupos/{gid}/liquidaciones",
                     json={"de_id": b, "a_id": a, "importe": 1000}).status_code == 201
    d = ana.get(f"/grupos/{gid}").json()
    assert d["transferencias"] == [] and len(d["liquidaciones"]) == 1

    gasto_id = d["gastos"][0]["id"]
    assert ana.delete(f"/grupos/{gid}/gastos/{gasto_id}").status_code == 204
    assert ana.get(f"/grupos/{gid}").json()["gastos"] == []


def test_un_no_miembro_recibe_404_en_todo(entorno):
    ana, a = _persona(entorno, "ana@ejemplo.com")
    intruso, i = _persona(entorno, "intruso@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "Privado"}).json()["id"]
    assert intruso.get(f"/grupos/{gid}").status_code == 404
    assert intruso.post(f"/grupos/{gid}/miembros", json={"email": "ana@ejemplo.com"}).status_code == 404
    assert intruso.post(f"/grupos/{gid}/recordatorios", json={"deudor_id": a}).status_code == 404
    assert intruso.post(f"/grupos/{gid}/gastos", json={
        "concepto": "x", "importe": 100, "pagador_id": i, "participantes": [i]}).status_code == 404
    assert intruso.get("/grupos").json() == []


def test_un_miembro_normal_no_puede_borrar_el_gasto_de_otro(entorno):
    ana, a = _persona(entorno, "ana@ejemplo.com")
    beto, b = _persona(entorno, "beto@ejemplo.com")
    carla, c = _persona(entorno, "carla@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "G"}).json()["id"]
    for email in ("beto@ejemplo.com", "carla@ejemplo.com"):
        ana.post(f"/grupos/{gid}/miembros", json={"email": email})
    gasto = beto.post(f"/grupos/{gid}/gastos", json={
        "concepto": "Taxi", "importe": 900, "pagador_id": b, "participantes": [a, b, c]}).json()
    r = carla.delete(f"/grupos/{gid}/gastos/{gasto['id']}")
    assert r.status_code == 403 and "error" in r.json()


def test_datos_invalidos_devuelven_400_con_mensaje(entorno):
    ana, a = _persona(entorno, "ana@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "G"}).json()["id"]
    r = ana.post(f"/grupos/{gid}/gastos",
                 json={"concepto": "Cena", "importe": -5, "pagador_id": a, "participantes": [a]})
    assert r.status_code == 400 and "mayor que 0" in r.json()["error"]
    assert ana.post("/grupos", json={"nombre": "  "}).status_code == 400
    assert ana.post(f"/grupos/{gid}/gastos", json={"concepto": "x"}).status_code == 422


def test_un_pago_mayor_que_la_deuda_devuelve_400_y_no_cambia_los_saldos(entorno):
    ana, a = _persona(entorno, "ana@ejemplo.com")
    beto, b = _persona(entorno, "beto@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "G"}).json()["id"]
    ana.post(f"/grupos/{gid}/miembros", json={"email": "beto@ejemplo.com"})
    ana.post(f"/grupos/{gid}/gastos",
             json={"concepto": "Cena", "importe": 2000, "pagador_id": a, "participantes": [a, b]})
    r = beto.post(f"/grupos/{gid}/liquidaciones", json={"de_id": b, "a_id": a, "importe": 50000})
    assert r.status_code == 400 and "como mucho 10,00 €" in r.json()["error"]
    d = ana.get(f"/grupos/{gid}").json()
    assert d["liquidaciones"] == []
    assert d["transferencias"] == [{"de_id": b, "a_id": a, "importe": 1000}]


def test_el_importe_decimal_no_se_acepta(entorno):
    # Los importes van en céntimos enteros: un 12.5 no es válido
    ana, a = _persona(entorno, "ana@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "G"}).json()["id"]
    r = ana.post(f"/grupos/{gid}/gastos",
                 json={"concepto": "Cena", "importe": 12.5, "pagador_id": a, "participantes": [a]})
    assert r.status_code == 422
