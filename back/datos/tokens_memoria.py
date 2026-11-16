from typing import Optional

from back.logica.tokens import RepositorioTokens, TokenConfirmacion


class RepositorioTokensMemoria(RepositorioTokens):
    def __init__(self):
        self._tokens: dict[str, TokenConfirmacion] = {}

    def guardar(self, token: TokenConfirmacion) -> None:
        self._tokens[token.clave] = token

    def obtener(self, clave: str) -> Optional[TokenConfirmacion]:
        return self._tokens.get(clave)

    def obtener_de_usuario(self, id_usuario: int) -> Optional[TokenConfirmacion]:
        return next((t for t in self._tokens.values() if t.id_usuario == id_usuario), None)

    def eliminar(self, clave: str) -> None:
        self._tokens.pop(clave, None)

    def eliminar_de_usuario(self, id_usuario: int) -> None:
        for clave in [c for c, t in self._tokens.items() if t.id_usuario == id_usuario]:
            del self._tokens[clave]
