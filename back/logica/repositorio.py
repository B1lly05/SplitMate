from abc import ABC, abstractmethod
from typing import Optional

from back.logica.modelos import Estado, Rol, Usuario


class RepositorioUsuarios(ABC):
    @abstractmethod
    def crear(self, email: str, rol: Rol, estado: Estado,
              password_hash: Optional[str] = None) -> Usuario: ...

    @abstractmethod
    def obtener_por_id(self, id: int) -> Optional[Usuario]: ...

    @abstractmethod
    def obtener_por_email(self, email: str) -> Optional[Usuario]: ...

    @abstractmethod
    def listar(self) -> list[Usuario]: ...

    @abstractmethod
    def actualizar(self, usuario: Usuario) -> None: ...