"""Implementación de los repositorios sobre MongoDB (capa de acceso a datos)."""
import hashlib
from datetime import timezone
from typing import Optional

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError

from back.logica.errores import EmailDuplicado
from back.logica.modelos import Estado, Rol, Usuario
from back.logica.repositorio import RepositorioUsuarios
from back.logica.sesiones import RepositorioSesiones, Sesion


class RepositorioUsuariosMongo(RepositorioUsuarios):
    def __init__(self, base):
        self._usuarios = base["usuarios"]
        self._contadores = base["contadores"]
        # El email es único a nivel de base de datos, aunque la lógica ya lo compruebe
        self._usuarios.create_index("email", unique=True)

    def _siguiente_id(self) -> int:
        doc = self._contadores.find_one_and_update(
            {"_id": "usuarios"},
            {"$inc": {"valor": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return doc["valor"]

    @staticmethod
    def _a_usuario(doc) -> Optional[Usuario]:
        if doc is None:
            return None
        return Usuario(
            id=doc["_id"],
            email=doc["email"],
            rol=Rol(doc["rol"]),
            estado=Estado(doc["estado"]),
            password_hash=doc.get("password_hash"),
        )

    def crear(self, email: str, rol: Rol, estado: Estado,
              password_hash: Optional[str] = None) -> Usuario:
        doc = {
            "_id": self._siguiente_id(),
            "email": email,
            "rol": rol.value,
            "estado": estado.value,
            "password_hash": password_hash,
        }
        try:
            self._usuarios.insert_one(doc)
        except DuplicateKeyError:
            raise EmailDuplicado("Ya existe un usuario con ese email")
        return self._a_usuario(doc)

    def obtener_por_id(self, id: int) -> Optional[Usuario]:
        return self._a_usuario(self._usuarios.find_one({"_id": id}))

    def obtener_por_email(self, email: str) -> Optional[Usuario]:
        return self._a_usuario(self._usuarios.find_one({"email": email}))

    def listar(self) -> list[Usuario]:
        return [self._a_usuario(d) for d in self._usuarios.find().sort("_id", 1)]

    def actualizar(self, usuario: Usuario) -> None:
        self._usuarios.update_one(
            {"_id": usuario.id},
            {"$set": {
                "email": usuario.email,
                "rol": usuario.rol.value,
                "estado": usuario.estado.value,
                "password_hash": usuario.password_hash,
            }},
        )


def _clave(token: str) -> str:
    # Se guarda solo el hash del token: si se filtrara la base de datos,
    # las sesiones activas no se podrían reutilizar.
    return hashlib.sha256(token.encode()).hexdigest()


class RepositorioSesionesMongo(RepositorioSesiones):
    def __init__(self, base):
        self._sesiones = base["sesiones"]
        # MongoDB borra solo las sesiones caducadas
        self._sesiones.create_index("expira_en", expireAfterSeconds=0)

    def guardar(self, sesion: Sesion) -> None:
        clave = _clave(sesion.token)
        self._sesiones.replace_one(
            {"_id": clave},
            {"_id": clave, "id_usuario": sesion.id_usuario, "expira_en": sesion.expira_en},
            upsert=True,
        )

    def obtener(self, token: str) -> Optional[Sesion]:
        doc = self._sesiones.find_one({"_id": _clave(token)})
        if doc is None:
            return None
        expira = doc["expira_en"]
        if expira.tzinfo is None:  # MongoDB devuelve fechas sin zona (UTC)
            expira = expira.replace(tzinfo=timezone.utc)
        return Sesion(token, doc["id_usuario"], expira)

    def eliminar(self, token: str) -> None:
        self._sesiones.delete_one({"_id": _clave(token)})


def crear_repositorios_mongo(uri: str, nombre_db: str):
    cliente = MongoClient(uri, serverSelectionTimeoutMS=5000)
    base = cliente[nombre_db]
    return RepositorioUsuariosMongo(base), RepositorioSesionesMongo(base)