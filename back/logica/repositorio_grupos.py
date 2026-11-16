from abc import ABC, abstractmethod
from typing import Optional

from back.logica.modelos import Gasto, Grupo, Liquidacion


class RepositorioGrupos(ABC):
    @abstractmethod
    def crear_grupo(self, nombre: str, creador_id: int) -> Grupo: ...

    @abstractmethod
    def obtener_grupo(self, id: int) -> Optional[Grupo]: ...

    @abstractmethod
    def listar_grupos_de(self, usuario_id: int) -> list[Grupo]: ...

    @abstractmethod
    def anadir_miembro(self, grupo_id: int, usuario_id: int) -> None: ...

    @abstractmethod
    def crear_gasto(self, grupo_id: int, concepto: str, importe: int, pagador_id: int,
                    participantes: list[int], creado_por: int, fecha: str) -> Gasto: ...

    @abstractmethod
    def obtener_gasto(self, id: int) -> Optional[Gasto]: ...

    @abstractmethod
    def listar_gastos(self, grupo_id: int) -> list[Gasto]: ...

    @abstractmethod
    def eliminar_gasto(self, id: int) -> None: ...

    @abstractmethod
    def crear_liquidacion(self, grupo_id: int, de_id: int, a_id: int, importe: int,
                          fecha: str) -> Liquidacion: ...

    @abstractmethod
    def listar_liquidaciones(self, grupo_id: int) -> list[Liquidacion]: ...
