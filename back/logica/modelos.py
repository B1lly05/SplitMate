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
    # Partes de cada participante (p. ej. adulto 2, niño 1). Si falta alguien, cuenta 1.
    pesos: dict[int, int] = field(default_factory=dict)


@dataclass
class Liquidacion:
    """Un pago real entre dos miembros que reduce lo que se debían."""
    id: int
    grupo_id: int
    de_id: int  # quien paga
    a_id: int   # quien recibe
    importe: int  # en céntimos
    fecha: str


@dataclass
class Actividad:
    """Una línea del historial del grupo: quién hizo qué y cuándo."""
    id: int
    grupo_id: int
    usuario_id: int
    tipo: str
    datos: dict
    fecha: str


@dataclass
class Invitacion:
    """Invitación a un grupo para un email que todavía no tiene cuenta activa."""
    id: int
    grupo_id: int
    email: str
    invitado_por: int
    creada_en: str
    expira_en: str
