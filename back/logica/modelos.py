from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
    password_hash: Optional[str] = None


@dataclass
class Grupo:
    id: int
    nombre: str
    creador_id: int
    miembros: list[int] = field(default_factory=list)


@dataclass
class Gasto:
    id: int
    grupo_id: int
    concepto: str
    importe: int  # en céntimos: con enteros no hay errores de redondeo
    pagador_id: int
    participantes: list[int]
    creado_por: int
    fecha: str  # ISO 8601


@dataclass
class Liquidacion:
    """Un pago real entre dos miembros que reduce lo que se debían."""
    id: int
    grupo_id: int
    de_id: int  # quien paga
    a_id: int   # quien recibe
    importe: int  # en céntimos
    fecha: str
