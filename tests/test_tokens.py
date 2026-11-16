from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from back.datos.mongo import RepositorioTokensMongo
from back.datos.tokens_memoria import RepositorioTokensMemoria
from back.logica.tokens import TokenConfirmacion

AHORA = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(params=["memoria", "mongo"])
def repo(request):
    if request.param == "memoria":
        return RepositorioTokensMemoria()
    return RepositorioTokensMongo(mongomock.MongoClient()["pruebas"])


def _token(clave="abc", id_usuario=1):
    return TokenConfirmacion(clave, id_usuario, AHORA, AHORA + timedelta(hours=24))


def test_guardar_y_obtener(repo):
    repo.guardar(_token())
    t = repo.obtener("abc")
    assert t.id_usuario == 1 and t.expira_en == AHORA + timedelta(hours=24)
    assert t.expira_en.tzinfo is not None


def test_obtener_un_token_inexistente_devuelve_none(repo):
    assert repo.obtener("nada") is None


def test_obtener_de_usuario(repo):
    repo.guardar(_token("a", 1))
    repo.guardar(_token("b", 2))
    assert repo.obtener_de_usuario(2).clave == "b"
    assert repo.obtener_de_usuario(3) is None


def test_eliminar(repo):
    repo.guardar(_token())
    repo.eliminar("abc")
    repo.eliminar("abc")  # borrar dos veces no falla
    assert repo.obtener("abc") is None


def test_eliminar_de_usuario_solo_borra_los_suyos(repo):
    repo.guardar(_token("a", 1))
    repo.guardar(_token("b", 2))
    repo.eliminar_de_usuario(1)
    assert repo.obtener("a") is None and repo.obtener("b") is not None
