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
    usuarios = ServicioUsuarios(RepositorioMemoria(), True)
    enviador = EnviadorSimulado()
    auth = ServicioAuth(usuarios, RepositorioSesionesMemoria())
    grupos = ServicioGrupos(RepositorioGruposMemoria(), usuarios, enviador,
                            "https://splitmate.ejemplo.com")
    app.dependency_overrides[get_servicio] = lambda: usuarios
    app.dependency_overrides[get_auth] = lambda: auth
    app.dependency_overrides[get_grupos] = lambda: grupos
    yield usuarios, enviador
    app.dependency_overrides.clear()


def _entrar(usuarios, email):
    usuario = usuarios.registrar(email, CLAVE)
    cliente = TestClient(app)
    assert cliente.post("/auth/login", json={"email": email, "password": CLAVE}).status_code == 200
    return cliente, usuario.id


def test_gasto_con_pesos_por_api(entorno):
    usuarios, _ = entorno
    ana, a = _entrar(usuarios, "ana@ejemplo.com")
    _, b = _entrar(usuarios, "beto@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "Piso"}).json()["id"]
    ana.post(f"/grupos/{gid}/miembros", json={"email": "beto@ejemplo.com"})
    r = ana.post(f"/grupos/{gid}/gastos", json={
        "concepto": "Alquiler", "importe": 3000, "pagador_id": a, "participantes": [a, b],
        "pesos": {str(a): 1, str(b): 2}})  # en JSON las claves siempre son texto
    assert r.status_code == 201
    d = ana.get(f"/grupos/{gid}").json()
    assert d["gastos"][0]["pesos"] == {str(b): 2}
    assert {s["usuario_id"]: s["saldo"] for s in d["saldos"]} == {a: 2000, b: -2000}


def test_un_peso_invalido_devuelve_400(entorno):
    usuarios, _ = entorno
    ana, a = _entrar(usuarios, "ana@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "Piso"}).json()["id"]
    r = ana.post(f"/grupos/{gid}/gastos", json={
        "concepto": "x", "importe": 100, "pagador_id": a, "participantes": [a], "pesos": {str(a): 99}})
    assert r.status_code == 400 and "error" in r.json()


def test_la_actividad_se_devuelve_en_el_detalle(entorno):
    usuarios, _ = entorno
    ana, a = _entrar(usuarios, "ana@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "Piso"}).json()["id"]
    ana.post(f"/grupos/{gid}/gastos", json={
        "concepto": "Cena", "importe": 500, "pagador_id": a, "participantes": [a]})
    actividad = ana.get(f"/grupos/{gid}").json()["actividad"]
    assert [e["tipo"] for e in actividad] == ["gasto_creado", "grupo_creado"]
    assert actividad[0]["datos"] == {"concepto": "Cena", "importe": 500}


def test_recordatorio_por_api(entorno):
    usuarios, enviador = entorno
    ana, a = _entrar(usuarios, "ana@ejemplo.com")
    beto, b = _entrar(usuarios, "beto@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "Piso"}).json()["id"]
    ana.post(f"/grupos/{gid}/miembros", json={"email": "beto@ejemplo.com"})
    ana.post(f"/grupos/{gid}/gastos", json={
        "concepto": "Cena", "importe": 3000, "pagador_id": a, "participantes": [a, b]})
    r = ana.post(f"/grupos/{gid}/recordatorios", json={"deudor_id": b})
    assert r.status_code == 202 and r.json() == {"importe": 1500}
    assert [d for d, *_ in enviador.recordatorios] == ["beto@ejemplo.com"]
    # el mismo día no se puede repetir, y quien debe no puede recordar a quien cobra
    assert ana.post(f"/grupos/{gid}/recordatorios", json={"deudor_id": b}).status_code == 400
    assert beto.post(f"/grupos/{gid}/recordatorios", json={"deudor_id": a}).status_code == 400


def test_invitar_a_alguien_sin_cuenta_por_api(entorno):
    usuarios, enviador = entorno
    ana, _ = _entrar(usuarios, "ana@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "Piso"}).json()["id"]
    r = ana.post(f"/grupos/{gid}/miembros", json={"email": "nuevo@ejemplo.com"})
    assert r.status_code == 201 and r.json()["resultado"] == "invitado"
    assert enviador.invitaciones[0][0] == "nuevo@ejemplo.com"
    assert ana.get(f"/grupos/{gid}").json()["invitaciones"][0]["email"] == "nuevo@ejemplo.com"

    # cuando esa persona se registra y entra, el grupo ya está en su lista
    nuevo, _ = _entrar(usuarios, "nuevo@ejemplo.com")
    assert [g["id"] for g in nuevo.get("/grupos").json()] == [gid]
    assert nuevo.get(f"/grupos/{gid}").status_code == 200


def test_si_el_correo_falla_la_api_responde_503_con_mensaje(entorno):
    usuarios, enviador = entorno
    ana, _ = _entrar(usuarios, "ana@ejemplo.com")
    gid = ana.post("/grupos", json={"nombre": "Piso"}).json()["id"]
    enviador.fallar = True
    r = ana.post(f"/grupos/{gid}/miembros", json={"email": "nuevo@ejemplo.com"})
    assert r.status_code == 503 and "correo" in r.json()["error"]
