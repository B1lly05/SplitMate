from dataclasses import dataclass
from enum import Enum


class Rol(str, Enum):
    USUARIO = "usuario"
    ADMIN = "admin"


class Estado(str, Enum):
    PENDIENTE = "pendiente"
    ACTIVO = "activo"
    ELIMINADO = "eliminado"


@dataclass
class Usuario:
    id: int
    email: str
    rol: Rol = Rol.USUARIO
    estado: Estado = Estado.PENDIENTE