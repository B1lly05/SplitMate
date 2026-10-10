from typing import Optional

from back.logica.sesiones import RepositorioSesiones, Sesion


class RepositorioSesionesMemoria(RepositorioSesiones):
    def __init__(self):
        self._sesiones: dict[str, Sesion] = {}

    def guardar(self, sesion: Sesion) -> None:
        self._sesiones[sesion.token] = sesion

    def obtener(self, token: str) -> Optional[Sesion]:
        return self._sesiones.get(token)

    def eliminar(self, token: str) -> None:
        self._sesiones.pop(token, None)