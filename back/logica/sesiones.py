from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Sesion:
    token: str
    id_usuario: int
    expira_en: datetime


class RepositorioSesiones(ABC):
    @abstractmethod
    def guardar(self, sesion: Sesion) -> None: ...

    @abstractmethod
    def obtener(self, token: str) -> Optional[Sesion]: ...

    @abstractmethod
    def eliminar(self, token: str) -> None: ...