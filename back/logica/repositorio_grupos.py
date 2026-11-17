from abc import ABC, abstractmethod
from typing import Optional

from back.logica.modelos import Actividad, Gasto, Grupo, Invitacion, Liquidacion


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
                    participantes: list[int], creado_por: int, fecha: str,
                    pesos: Optional[dict[int, int]] = None) -> Gasto: ...

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

    @abstractmethod
    def registrar_actividad(self, grupo_id: int, usuario_id: int, tipo: str, datos: dict,
                            fecha: str) -> Actividad: ...

    @abstractmethod
    def listar_actividad(self, grupo_id: int, limite: int) -> list[Actividad]:
        """Las últimas entradas del historial, la más reciente primero."""

    @abstractmethod
    def crear_invitacion(self, grupo_id: int, email: str, invitado_por: int, creada_en: str,
                         expira_en: str) -> Invitacion: ...

    @abstractmethod
    def listar_invitaciones_de_grupo(self, grupo_id: int) -> list[Invitacion]: ...

    @abstractmethod
    def listar_invitaciones_para(self, email: str) -> list[Invitacion]: ...

    @abstractmethod
    def eliminar_invitacion(self, id: int) -> None: ...
