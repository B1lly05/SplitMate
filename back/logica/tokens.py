from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TokenConfirmacion:
    clave: str  # SHA-256 del token: el token en claro solo existe en el correo
    id_usuario: int
    creado_en: datetime
    expira_en: datetime


class RepositorioTokens(ABC):
    @abstractmethod
    def guardar(self, token: TokenConfirmacion) -> None: ...

    @abstractmethod
    def obtener(self, clave: str) -> Optional[TokenConfirmacion]: ...

    @abstractmethod
    def obtener_de_usuario(self, id_usuario: int) -> Optional[TokenConfirmacion]: ...

    @abstractmethod
    def eliminar(self, clave: str) -> None: ...

    @abstractmethod
    def eliminar_de_usuario(self, id_usuario: int) -> None: ...
